"""Run and report the preregistered Terra/Sonnet scientific repair comparison."""

import argparse
import os
import re
import subprocess
from pathlib import Path

from . import client, dispatch, report, study

PROTOCOL = study.HERE / "repair-protocol.json"
ARMS = ("draft", "ordinary", "repair")


def validate_protocol(out):
    protocol = study.read(PROTOCOL)
    design, groups = study.freeze(out, "frontier")
    skill = study.skill_text(protocol["skill"])
    tasks = protocol["tasks"]
    excluded = set(protocol["previously_started"])
    if (
        study.digest(skill) != protocol["skill_sha256"]
        or study.digest((study.HERE / "frontier-development.json").read_text())
        != protocol["development_audit_sha256"]
        or excluded & tasks.keys()
        or tasks
        != {k: v for k, v in design["tasks"]["holdout"].items() if k not in excluded}
        or len(tasks) != 12
        or tuple(protocol["models"]) != study.PRIMARY
        or not (out / "frontier/interventions.json").is_file()
    ):
        raise ValueError("Frozen skill, development evidence or holdout design changed")
    return protocol, skill, {c["id"]: c for c in groups["holdout"]}


def assignment(out, task, model, protocol, *, components=None, validated_rows=None):
    """Only scores from the original engine, parent draft and frozen skill enter a pair."""
    folder = out / "frontier"
    placement = folder / "execution-contexts" / (task + ".json")
    if not placement.exists():
        return {arm: {"outcome": "missing"} for arm in ARMS}
    machine = study.read(placement)
    if not study.placement_control_matches(
        task, machine, control_root=out / "frontier-controls"
    ):
        return {arm: {"outcome": "unverified_engine"} for arm in ARMS}
    identity = report._docker_identity(
        {
            "participant_context": machine["context"],
            "participant_engine": machine["engine"],
        }
    )
    controls = report._controls(out / "frontier-controls", "frontier", task, "holdout")
    qualified = any(
        report._verified(c) for c in report._match_controls(controls, identity)
    )
    scores = {}
    draft = None
    for arm in ARMS:
        path = study.row_path(out, "frontier", "holdout", {"id": task}, model, arm)
        if not path.is_file():
            scores[arm] = {"outcome": "missing"}
            continue
        row = study.read(path)
        key = tuple(
            row.get(field) for field in ("track", "phase", "task", "model", "arm")
        )
        if key != ("frontier", "holdout", task, model, arm):
            raise ValueError(f"Assignment identity mismatch: {path.name}")
        if not qualified or report._docker_identity(row) != identity:
            scores[arm] = {"outcome": "unverified_engine"}
            continue
        if (
            arm == "repair"
            and row.get("review_skill_sha256") != protocol["skill_sha256"]
        ):
            scores[arm] = {"outcome": "unverified_skill"}
            continue
        if arm != "draft" and (
            not draft or row.get("parent_scheme") != "participant-v1"
        ):
            scores[arm] = {"outcome": "unverified_draft"}
            continue
        if arm != "draft" and row["status"] == "submitted":
            expected_history = {
                "PRIOR_WORK.json": study.digest(
                    study.encode(draft["session"]["calls"])
                ),
                "PRIOR_REPLY.txt": study.digest(draft["session"]["reply"]),
            }
            if (row.get("session") or {}).get(
                "review_context_sha256"
            ) != expected_history:
                scores[arm] = {"outcome": "unverified_review_history"}
                continue
        session = row.get("session") or {}
        auth = (session.get("subscription") or {}).get("auth") or {}
        if row["status"] == "submitted":
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", row.get("image") or ""):
                scores[arm] = {"outcome": "unverified_snapshot"}
                continue
            if (
                auth.get("claude_api_provider") != "firstParty"
                or auth.get("claude_extra_usage") is not False
                or auth.get("codex") != "ChatGPT"
                or auth.get("codex_included_usage_available") is not True
                or row.get("recovery", {}).get("subscription_receipt_binding")
                == "historical_nearest_unverified"
            ):
                scores[arm] = {"outcome": "unverified_subscription"}
                continue
            if session.get("model") != client.MODELS[model] or session.get(
                "reported_model"
            ) not in (None, client.MODELS[model]):
                scores[arm] = {"outcome": "unverified_model"}
                continue
            if session.get("client_deadline_reached") and (
                not session.get("cutoff_image")
                or row.get("image") != session["cutoff_image"]
            ):
                scores[arm] = {"outcome": "unverified_deadline"}
                continue
            score = row.get("score") or {}
            if type(score.get("correct")) is bool and (
                not report.number(score.get("reward"))
                or not 0 <= score["reward"] <= 1
                or score["correct"] != (score["reward"] == 1)
            ):
                scores[arm] = {"outcome": "unverified_reward"}
                continue
        scores[arm] = report.public_row(row, draft, None)
        if type(scores[arm].get("correct")) is bool:
            if arm == "draft":
                draft = row
            if validated_rows is not None:
                validated_rows[arm] = row
            if components is not None:
                components[arm] = row["score"].get("private_component_status", {})
            identity_hash = (
                study.draft_identity(row) if arm == "draft" else row["parent"]
            )
            scores[arm]["draft_sha256"] = identity_hash
            scores[arm]["model_identity"] = (
                "provider_reported"
                if session.get("reported_model")
                else "requested_only"
            )
    return scores


def run(out, selected, models):
    protocol, skill, cases = validate_protocol(out)
    if set(selected) - protocol["tasks"].keys() or set(models) - set(
        protocol["models"]
    ):
        raise ValueError("Task or model outside frozen repair cohort")
    original_context = os.environ.get("DOCKER_CONTEXT")
    blocked = []
    errors = (OSError, ValueError, RuntimeError, subprocess.SubprocessError)

    def record(task, model, arm, reason):
        message = f"{task}/{model}/{arm}: {reason}"
        print(message, flush=True)
        blocked.append(message)

    try:
        for task in selected:
            try:
                placement = dispatch.reserve_context(out / "frontier", task, {})
            except errors as exc:
                record(task, "*", "placement", exc)
                continue
            os.environ["DOCKER_CONTEXT"] = placement["context"]
            for model in models:
                reviews = sorted(
                    ARMS[1:],
                    key=lambda a: study.digest(f"repair-v1/{task}/{model}/{a}"),
                )
                for arm in ("draft", *reviews):
                    try:
                        study.run_one(
                            (
                                out,
                                "frontier",
                                "holdout",
                                cases[task],
                                model,
                                arm,
                                {"repair": skill},
                            )
                        )
                        grade = assignment(out, task, model, protocol)[arm]
                        if type(grade.get("correct")) is not bool:
                            raise RuntimeError(
                                f"unscored ({grade.get('reason', grade['outcome'])})"
                            )
                    except errors as exc:
                        record(task, model, arm, exc)
                        if arm == "draft":
                            break
    finally:
        if original_context is None:
            os.environ.pop("DOCKER_CONTEXT", None)
        else:
            os.environ["DOCKER_CONTEXT"] = original_context
    return blocked


def matched_components(statuses):
    """Count same-check transitions without publishing evaluator names or parameters."""
    if not all(statuses.get(arm) for arm in ARMS):
        return None
    draft, ordinary, repair = (statuses[a] for a in ARMS)
    if draft.keys() != ordinary.keys() or draft.keys() != repair.keys():
        return None
    counts = {
        "comparable": 0,
        "other": 0,
        "both_fixed": 0,
        "ordinary_only_fixed": 0,
        "skill_only_fixed": 0,
        "both_broke": 0,
        "ordinary_only_broke": 0,
        "skill_only_broke": 0,
    }
    for name in draft:
        steps = draft[name], ordinary[name], repair[name]
        if any(s not in ("passed", "failed") for s in steps):
            counts["other"] += 1
            continue
        counts["comparable"] += 1
        first, normal, skill = steps
        if first == normal == skill:
            continue
        suffix = "fixed" if first == "failed" else "broke"
        which = (
            "both"
            if normal == skill
            else "ordinary_only"
            if normal != first
            else "skill_only"
        )
        counts[which + "_" + suffix] += 1
    return counts


def session_effort(row):
    """Export session wall time and the number of structurally valid shell receipts."""
    session = row["session"]
    seconds = session.get("elapsed_seconds")
    calls = session.get("calls")
    if row.get("recovery") or not report.number(seconds) or seconds < 0:
        return None
    if not isinstance(calls, list) or not all(
        isinstance(call, dict)
        and isinstance(call.get("code"), str)
        and isinstance(call.get("output"), str)
        and type(call.get("status")) is int
        for call in calls
    ):
        return None
    return {"elapsed_seconds": seconds, "tool_calls": len(calls)}


def observation(out, task, model, protocol):
    statuses = {}
    rows = {}
    arms = assignment(
        out, task, model, protocol, components=statuses, validated_rows=rows
    )
    row = {"task": task, "model": model, "arms": arms}
    if all(type(arms[a].get("correct")) is bool for a in ARMS):
        row["component_transitions"] = matched_components(statuses)
        effort = {arm: session_effort(rows[arm]) for arm in ("ordinary", "repair")}
        if all(effort.values()):
            row["review_effort"] = effort
    return row


def export(out):
    protocol, _, _ = validate_protocol(out)
    return {
        "protocol_sha256": study.digest(PROTOCOL.read_text()),
        "skill_sha256": protocol["skill_sha256"],
        "tasks": list(protocol["tasks"]),
        "models": protocol["models"],
        "observations": [
            observation(out, task, model, protocol)
            for task in protocol["tasks"]
            for model in protocol["models"]
        ],
    }


def summarize(archive, protocol):
    expected = {(t, m) for t in protocol["tasks"] for m in protocol["models"]}
    if (
        archive["protocol_sha256"] != study.digest(PROTOCOL.read_text())
        or archive["skill_sha256"] != protocol["skill_sha256"]
    ):
        raise ValueError("Archive does not match frozen intervention")
    rows = archive["observations"]
    keys = [(r["task"], r["model"]) for r in rows]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError("Missing, duplicate or unexpected assignment")
    matched = []
    for row in rows:
        arms = row["arms"]
        if all(type(arms[a].get("correct")) is bool for a in ARMS):
            draft_hash = arms["draft"].get("draft_sha256")
            if not re.fullmatch(r"[0-9a-f]{64}", draft_hash or "") or any(
                arms[a].get("draft_sha256") != draft_hash for a in ARMS[1:]
            ):
                raise ValueError(
                    f"Inconsistent public draft fingerprints for {row['task']}/{row['model']}"
                )
            matched.append(
                (row["task"], row["model"], *(arms[a]["correct"] for a in ARMS))
            )
    repairs = [(t, m) for t, m, d, o, s in matched if not d and not o and s]
    regressions = [(t, m) for t, m, d, o, s in matched if o and not s]
    broken_drafts = [(t, m) for t, m, d, o, s in matched if d and not s]
    net = sum(int(s) - int(o) for _, _, _, o, s in matched)
    distinct = len({t for t, _ in repairs})
    finished = len(matched) == len(expected)
    return {
        "matched": len(matched),
        "scheduled": len(expected),
        "draft_passes": sum(d for _, _, d, _, _ in matched),
        "ordinary_passes": sum(o for _, _, _, o, _ in matched),
        "repair_passes": sum(s for _, _, _, _, s in matched),
        "net": net,
        "distinct": distinct,
        "repairs": repairs,
        "ordinary_only": regressions,
        "broken_drafts": broken_drafts,
        "target": (
            "met"
            if distinct >= protocol["minimum_distinct_repaired_tasks"]
            and net >= protocol["minimum_net_additional_passes"]
            else "missed"
        )
        if finished
        else "pending",
    }


def review_effort_table(observations, matched):
    """Report both review costs only when a complete comparison has both receipts."""
    pairs = []
    for row in observations:
        arms = row["arms"]
        if not all(type(arms[a].get("correct")) is bool for a in ARMS):
            continue
        effort = row.get("review_effort")
        if not isinstance(effort, dict):
            continue
        ordinary, skill = effort.get("ordinary"), effort.get("repair")
        if all(
            isinstance(a, dict)
            and report.number(a.get("elapsed_seconds"))
            and a["elapsed_seconds"] >= 0
            and type(a.get("tool_calls")) is int
            and a["tool_calls"] >= 0
            for a in (ordinary, skill)
        ):
            pairs.append((row, ordinary, skill))
    if not pairs:
        return []
    lines = [
        "",
        "## Review time and tool use",
        "",
        f"Both review sessions have recorded wall time and shell requests for {len(pairs)} of {matched} complete comparisons. Wall time includes staging and cleanup. Each logged shell request counts once, including requests that returned an error.",
        "",
        "| Task and model | Ordinary seconds | Skill seconds | Ordinary shell requests | Skill shell requests |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row, ordinary, skill in pairs:
        lines.append(
            f"| {row['task']} ({row['model']}) | {ordinary['elapsed_seconds']:.2f} | {skill['elapsed_seconds']:.2f} | {ordinary['tool_calls']} | {skill['tool_calls']} |"
        )
    fields = [
        f"{sum(pair[i]['elapsed_seconds'] for pair in pairs):.2f}" for i in (1, 2)
    ] + [str(sum(pair[i]["tool_calls"] for pair in pairs)) for i in (1, 2)]
    lines.append("| **Total** | " + " | ".join(fields) + " |")
    return lines


def render(archive):
    result = summarize(archive, study.read(PROTOCOL))

    def listing(items):
        return ", ".join(f"{t} ({m})" for t, m in items) or "None"

    available = {
        a: sum(
            type(r["arms"][a].get("correct")) is bool for r in archive["observations"]
        )
        for a in ARMS
    }
    lines = [
        "# Scientific repair holdout",
        "",
        f"Target **{result['target']}**. Complete three-arm comparisons **{result['matched']}/{result['scheduled']}**.",
        "",
        "| | First draft | Ordinary review | Repair skill |",
        "| --- | ---: | ---: | ---: |",
        f"| Scored assignments | {available['draft']} | {available['ordinary']} | {available['repair']} |",
    ]
    if result["matched"]:
        lines.extend(
            [
                f"| Full passes among complete comparisons | {result['draft_passes']} | {result['ordinary_passes']} | {result['repair_passes']} |",
                "",
                f"The skill earned {result['net']:+d} net full passes over ordinary review. It repaired {result['distinct']} distinct tasks on which both the draft and ordinary review failed.",
                "",
                f"- Skill-only repairs of wrong drafts — {listing(result['repairs'])}.",
                f"- Ordinary-only full passes — {listing(result['ordinary_only'])}.",
                f"- Correct drafts broken by the skill — {listing(result['broken_drafts'])}.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "The additional full passes and regressions can be estimated once a matched comparison is available.",
            ]
        )
    lines.extend(
        [
            "",
            "## Outcomes by task",
            "",
            "Scores below are upstream rewards. A full pass earns 1. Where the verifier reports individual checks, the table gives passed and failed counts. Differences in check counts can reveal partial repairs or regressions even when both rewards are zero.",
            "",
            "| Task | Model | First draft | Ordinary review | Repair skill |",
            "| --- | --- | --- | --- | --- |",
        ]
    )

    def cell(arm):
        if type(arm.get("correct")) is not bool:
            return arm.get("reason", arm["outcome"]).replace("_", " ")
        totals = arm.get("pytest_outcomes") or arm.get("checks") or {}
        counts = ", ".join(f"{n} {k}" for k, n in sorted(totals.items()))
        return f"{arm['reward']:g}" + (f" ({counts})" if counts else "")

    for row in archive["observations"]:
        values = [row["task"], row["model"], *(cell(row["arms"][arm]) for arm in ARMS)]
        lines.append("| " + " | ".join(values) + " |")
    if result["matched"]:
        lines.extend(
            [
                "",
                "## Individual scientific checks",
                "",
                "Each change below compares the same upstream check across all three arms. A fix changes a failed draft check to a pass. A regression changes a passing draft check to a failure. These component changes do not count toward the full-task target.",
                "",
                "| Task and model | Comparable | Both fixed | Ordinary alone fixed | Skill alone fixed | Both broke | Ordinary alone broke | Skill alone broke | Skipped or other |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in archive["observations"]:
            if not all(type(row["arms"][a].get("correct")) is bool for a in ARMS):
                continue
            c = row.get("component_transitions")
            counts = (
                [
                    str(c[k])
                    for k in (
                        "comparable",
                        "both_fixed",
                        "ordinary_only_fixed",
                        "skill_only_fixed",
                        "both_broke",
                        "ordinary_only_broke",
                        "skill_only_broke",
                        "other",
                    )
                ]
                if c
                else ["unavailable", *(["—"] * 7)]
            )
            lines.append(
                "| "
                + " | ".join([row["task"] + " (" + row["model"] + ")", *counts])
                + " |"
            )
    lines.extend(review_effort_table(archive["observations"], result["matched"]))
    lines.extend(["", "[Protocol and interpretation](../repair-study.md)", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("run", "export", "render"))
    parser.add_argument("--out", type=Path, default=study.DEFAULT_OUT)
    parser.add_argument("--tasks", nargs="+")
    parser.add_argument(
        "--models", nargs="+", choices=study.PRIMARY, default=study.PRIMARY
    )
    parser.add_argument(
        "--archive", type=Path, default=study.HERE / "results/repair-archive.json"
    )
    parser.add_argument(
        "--report", type=Path, default=study.HERE / "results/repair-results.md"
    )
    args = parser.parse_args()
    if args.action == "run":
        if run(
            args.out, args.tasks or list(study.read(PROTOCOL)["tasks"]), args.models
        ):
            raise SystemExit(
                "Some assignments remain incomplete. See the per-assignment reasons."
            )
    else:
        archive = (
            export(args.out) if args.action == "export" else study.read(args.archive)
        )
        output = render(archive)
        if args.action == "export":
            study.save(args.archive, archive)
        args.report.write_text(output)


if __name__ == "__main__":
    main()
