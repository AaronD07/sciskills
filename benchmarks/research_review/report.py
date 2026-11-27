"""Export anonymized results and render matched, same-draft comparisons offline."""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from . import everyday, study

ARMS = ("draft", *study.ARMS)
CHECKS = (
    "state",
    "value",
    "unit",
    "evidence",
    "gap",
    "authorized",
    "state_matches",
    "original_inputs",
)
KNOWN_STATUS = {
    "submitted",
    "quota_exhausted",
    "authentication_error",
    "model_unavailable",
    "cli_error",
    "oversize_transcript",
    "model_identity_mismatch",
    "unexpected_tool",
    "invalid_cli_output",
    "incomplete_turn",
    "timeout",
    "tool_unavailable",
    "invalid_receipt",
    "unreplayable_workspace",
    "missing_artifact",
    "invalid_submission",
    "patch_capture_error",
    "missing_patch",
    "verifier_timeout",
    "verifier_no_reward",
    "verifier_bad_reward",
    "verifier_no_binary_reward",
    "graded",
}


def number(value):
    if type(value) is int:
        return value.bit_length() < 1024
    return type(value) is float and math.isfinite(value)


def safe_status(value):
    return value if value in KNOWN_STATUS else "unknown_error"


def measurements(case, raw, draft):
    """Extract only fixture-defined fields and numeric answers, never arbitrary text."""
    submitted = {}
    for part in (draft, raw):
        if not part:
            continue
        session = part["session"]
        if everyday.OUTPUT in session["artifacts"]:
            try:
                submitted = json.loads(session["artifacts"][everyday.OUTPUT])
            except (ValueError, TypeError):
                submitted = {}
        if everyday.OUTPUT in session["deleted"]:
            submitted = {}
    if not isinstance(submitted, dict):
        submitted = {}
    key = case["key"]
    observed = submitted.get("value")
    state = submitted.get("state")
    result = {
        "expected": key["value"],
        "unit": key["unit"],
        "state": (state if state in ("complete", "pending") else "unavailable"),
        "observed": observed if number(observed) else None,
    }
    evidence = submitted.get("evidence")
    if isinstance(evidence, dict):
        result["discrepancies"] = {
            name: {
                "expected": target,
                "observed": evidence.get(name) if number(evidence.get(name)) else None,
            }
            for name, target in key["evidence"].items()
            if not everyday._number(evidence.get(name), target)
        }
    return result


def public_row(raw, draft, case):
    score = raw.get("score") or {}
    status = safe_status(raw["status"])
    if raw["arm"] != "draft" and (
        not draft
        or raw["parent"]
        != (
            study.draft_identity(draft)
            if raw.get("parent_scheme") == "participant-v1"
            else study.digest(study.encode(draft))
        )
    ):
        return {"outcome": "lineage_error", "reason": "unverified_draft"}
    if status != "submitted":
        kind = (
            "incomplete"
            if status in {"timeout", "incomplete_turn"}
            else "infrastructure"
        )
        return {"outcome": kind, "reason": status}
    result = score.get("correct")
    if type(result) is not bool:
        return {
            "outcome": "ungraded" if not score else "infrastructure",
            "reason": safe_status(score.get("status")) if score else "awaiting_grade",
        }
    invalid = score.get("valid") is False or score.get("status") in {
        "invalid_submission",
        "missing_artifact",
    }
    summary = {"outcome": "invalid" if invalid else "graded", "correct": result}
    details = score.get("details", {})
    summary["failed_checks"] = [k for k in CHECKS if details.get(k) is False]
    if case:
        summary["family"] = case["family"]
        summary["measurement"] = measurements(case, raw, draft)
    else:
        # The score, aggregate check counts and artifact presence are safe to publish.
        if number(score.get("reward")):
            summary["reward"] = score["reward"]
        summary["checks"] = {
            k: n
            for k, n in score.get("checks", {}).items()
            if k in ("passed", "failed", "skipped", "pending", "other")
            and type(n) is int
        }
        summary["pytest_outcomes"] = {
            k: n
            for k, n in score.get("pytest_outcomes", {}).items()
            if k
            in ("passed", "failed", "skipped", "error", "errors", "xfailed", "xpassed")
            and type(n) is int
        }
        summary["missing_artifacts"] = len(score.get("missing", []))
    return summary


def archive_runs(root, tracks=study.TRACKS):
    """Build an allowlisted archive from local primary records, independent of wall time."""
    archive = {"schema_version": 1, "tracks": {}, "rows": []}
    for track in sorted(tracks):
        directory = root / track
        if not (directory / "design.json").is_file():
            continue
        design = study.read(directory / "design.json")
        frozen = {
            "study": design["study"],
            "effort": design["effort"],
            "tasks": design["tasks"],
            "transfer_ids": design["transfer_ids"],
            "primary": design["primary"],
            "transfer": design["transfer"],
            "sealed": (directory / "interventions.json").is_file(),
        }
        if frozen["sealed"]:
            skills = study.read(directory / "interventions.json")
            frozen["general_sha256"] = study.digest(skills["general"])
            frozen["specialist_sha256"] = {
                t: study.digest(text) for t, text in skills["specialist"].items()
            }
        if track != "everyday":
            frozen["controls"] = {}
            for ids in design["tasks"].values():
                for task in sorted(ids):
                    control = root / (track + "-controls") / (task + ".json")
                    if control.is_file():
                        receipt = study.read(control)
                        frozen["controls"][task] = {
                            "ready": receipt.get("ready") is True,
                            "negative_correct": (receipt.get("negative") or {}).get(
                                "correct"
                            ),
                            "positive_correct": (receipt.get("positive") or {}).get(
                                "correct"
                            ),
                        }
        archive["tracks"][track] = frozen
        for phase, ids in sorted(frozen["tasks"].items()):
            ev = (
                {c["id"]: c for c in everyday.cases(phase)}
                if track == "everyday"
                else {}
            )
            observed = {p.name for p in (directory / phase).glob("*.json")}
            for task in sorted(ids):
                models = design["primary"] + (
                    design["transfer"]
                    if phase == "holdout" and task in design["transfer_ids"]
                    else []
                )
                for model in sorted(models):
                    draft = None
                    for arm in ARMS if phase == "holdout" else ("draft",):
                        name = f"{task}.{model}.{arm}.json"
                        if name not in observed:
                            continue
                        observed.remove(name)
                        path = directory / phase / name
                        row = study.read(path)
                        identity = {
                            "track": track,
                            "phase": phase,
                            "task": task,
                            "model": model,
                            "arm": arm,
                        }
                        if any(row[k] != v for k, v in identity.items()):
                            raise ValueError(f"Session identity mismatch for {name}")
                        grade = public_row(row, draft, ev.get(task))
                        session = row.get("session", {})
                        if session.get("reported_model") == session.get(
                            "model"
                        ) and session.get("reported_model"):
                            grade["model_identity"] = "provider_reported"
                        elif session.get("model"):
                            grade["model_identity"] = "requested_only"
                        if number(session.get("elapsed_seconds")):
                            grade["elapsed_seconds"] = session["elapsed_seconds"]
                        if isinstance(session.get("calls"), list):
                            grade["tool_calls"] = len(session["calls"])
                        if session.get("termination") == "task_deadline":
                            grade["task_deadline"] = True
                        previous = path.parent / "failed-attempts" / name
                        if previous.is_file():
                            grade["previous_attempt"] = safe_status(
                                study.read(previous)["status"]
                            )
                        archive["rows"].append({**identity, **grade})
                        if arm == "draft":
                            draft = row
            if observed:
                raise ValueError(
                    f"Unexpected sessions outside frozen design: {sorted(observed)}"
                )
    return archive


def paired(rows, before, after):
    """Return matched counts and task IDs; each observation is one model on one task."""
    pairs = [
        (task, arms[before]["correct"], arms[after]["correct"])
        for task, arms in sorted(rows.items())
        if all("correct" in arms.get(arm, {}) for arm in (before, after))
    ]
    return {
        "n": len(pairs),
        "before": sum(a for _, a, _ in pairs),
        "after": sum(b for _, _, b in pairs),
        "repairs": [t for t, a, b in pairs if not a and b],
        "regressions": [t for t, a, b in pairs if a and not b],
    }


def witness(row):
    """Describe the observed scientific discrepancy with only published evidence."""
    if row["outcome"] == "invalid":
        return "missing or malformed submission"
    m = row.get("measurement")
    checks = row.get("failed_checks", [])
    if m:
        facts = []
        if "value" in checks:
            if m["expected"] is None:
                facts.append(
                    f"reported {m['observed']} {m['unit']} with a missing input"
                )
            else:
                facts.append(
                    f"reported {m['observed']}, expected {m['expected']} {m['unit']}"
                )
        if "evidence" in checks:
            facts.extend(
                f"{k} was {v['observed']}, expected {v['expected']}"
                for k, v in m.get("discrepancies", {}).items()
            )
        names = {
            "gap": "required clarification missing or misplaced",
            "authorized": "unauthorized register write",
            "state_matches": "final register differed",
            "original_inputs": "source inputs altered",
            "state": "incorrect completion state",
            "unit": "incorrect reporting unit",
        }
        facts.extend(names[c] for c in checks if c in names)
        return ", ".join(facts) or "all required checks passed"
    totals = ", ".join(f"{n} {k}" for k, n in sorted(row.get("checks", {}).items()))
    return f"upstream reward {row.get('reward', 0):g}" + (
        f" ({totals})" if totals else ""
    )


def render(archive):
    if archive.get("schema_version") != 1:
        raise ValueError("Unsupported results schema")
    lines = [
        "# Research review results",
        "",
        "Each comparison uses the same task, model and frozen first draft. A malformed submission counts as incorrect. "
        "Missing sessions, incomplete turns, unverified draft links and infrastructure failures are excluded from paired denominators.",
        "",
    ]
    by_group = defaultdict(dict)
    for r in archive["rows"]:
        by_group[r["track"], r["phase"], r["model"], r["task"]][r["arm"]] = r
    for track, design in sorted(archive["tracks"].items()):
        for phase in ("dev", "holdout"):
            lines.extend([f"## {track.capitalize()} {phase}", ""])
            if "controls" in design:
                controls = [
                    design["controls"][t]
                    for t in design["tasks"][phase]
                    if t in design["controls"]
                ]
                ready = sum(c["ready"] for c in controls)
                remaining = len(design["tasks"][phase]) - len(controls)
                label = (
                    "empty and reference submission"
                    if track == "frontier"
                    else "empty submission"
                )
                lines.extend(
                    [
                        f"Upstream {label} control counts are {ready} ready, {len(controls) - ready} failed and {remaining} without a receipt.",
                        "",
                    ]
                )
            if (
                phase == "holdout"
                and not design["sealed"]
                and not any(k[:2] == (track, phase) for k in by_group)
            ):
                lines.extend(
                    [
                        "Holdouts have been frozen. Review interventions have yet to be sealed.",
                        "",
                    ]
                )
                continue
            lines.extend(
                [
                    "| Cohort | Model | Arm | Correct / scored | Invalid¹ | Missing | Incomplete | Ungraded | Infrastructure | Lineage errors | Task deadline² |",
                    "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
                ]
            )
            matched, cases, behaviors = [], [], []
            for cohort in (
                ("primary", "transfer") if phase == "holdout" else ("primary",)
            ):
                for model in design[cohort]:
                    ids = (
                        design["tasks"][phase]
                        if cohort == "primary"
                        else design["transfer_ids"]
                    )
                    rows = {
                        t: by_group.get((track, phase, model, t), {})
                        for t in sorted(ids)
                    }
                    for arm in ARMS if phase == "holdout" else ("draft",):
                        observed = [a[arm] for a in rows.values() if arm in a]
                        status = Counter(r["outcome"] for r in observed)
                        correct = sum(r.get("correct") is True for r in observed)
                        scored = sum("correct" in r for r in observed)
                        deadlines = sum(
                            r.get("task_deadline") is True for r in observed
                        )
                        lines.append(
                            f"| {cohort} | {model} | {arm} | {correct}/{scored} | {status['invalid']} | {len(ids) - len(observed)} | {status['incomplete']} | {status['ungraded']} | {status['infrastructure']} | {status['lineage_error']} | {deadlines} |"
                        )
                        measured = [
                            r
                            for r in observed
                            if r.get("outcome") == "graded" and "measurement" in r
                        ]
                        if measured:
                            pending = [
                                r
                                for r in measured
                                if r["measurement"]["expected"] is None
                            ]
                            answerable = [
                                r
                                for r in measured
                                if r["measurement"]["expected"] is not None
                            ]
                            unsupported = sum(
                                r["measurement"]["state"] == "complete"
                                or r["measurement"]["observed"] is not None
                                for r in pending
                            )
                            abstentions = sum(
                                r["measurement"]["state"] == "pending"
                                for r in answerable
                            )
                            scope = sum(
                                "authorized" in r["failed_checks"] for r in measured
                            )
                            behaviors.append(
                                f"| {model} | {arm} | {unsupported}/{len(pending)} | {abstentions}/{len(answerable)} | {scope}/{len(measured)} |"
                            )
                    if phase == "dev":
                        for task, arms in rows.items():
                            draft = arms.get("draft", {})
                            if draft.get("correct") is False:
                                cases.append(f"* {model}, `{task}` — {witness(draft)}.")
                        continue
                    for before, after in [("draft", a) for a in study.ARMS] + [
                        ("ordinary", "general"),
                        ("ordinary", "specialist"),
                    ]:
                        pair = paired(rows, before, after)
                        matched.append(
                            f"| {model} | {before} → {after} | {pair['n']} | {pair['before']} → {pair['after']} | {len(pair['repairs'])} | {len(pair['regressions'])} |"
                        )
                    for task, arms in rows.items():
                        draft = arms.get("draft", {})
                        ordinary = arms.get("ordinary", {})
                        if all(arms.get(a, {}).get("correct") is False for a in ARMS):
                            cases.append(
                                f"* {model}, `{task}` — all four submissions failed. The draft showed {witness(draft)}."
                            )
                        for arm in ("general", "specialist"):
                            skill = arms.get(arm, {})
                            if not all(
                                "correct" in r for r in (draft, ordinary, skill)
                            ):
                                continue
                            if ordinary["correct"] == skill["correct"]:
                                if skill["correct"] != draft["correct"]:
                                    event = (
                                        "repair shared with ordinary review"
                                        if skill["correct"]
                                        else "regression shared with ordinary review"
                                    )
                                    failed = draft if skill["correct"] else skill
                                    cases.append(
                                        f"* {model}, {arm}, `{task}` — {event}. The failing arm showed {witness(failed)}."
                                    )
                                continue
                            if skill["correct"]:
                                event = (
                                    "unique repair"
                                    if not draft["correct"]
                                    else "preserved correct draft"
                                )
                                evidence = witness(ordinary)
                            else:
                                event = (
                                    "new regression"
                                    if draft["correct"]
                                    else "missed ordinary repair"
                                )
                                evidence = witness(skill)
                            cases.append(
                                f"* {model}, {arm}, `{task}` — {event}. The failing arm showed {evidence}."
                            )
            lines.extend(
                [
                    "",
                    "¹ Invalid submissions are included in the scored denominator.",
                    "² The agent reached its task budget after using a tool. Its saved work was submitted for grading.",
                    "",
                ]
            )
            if behaviors:
                lines.extend(
                    [
                        "| Model | Arm | Unsupported completion / unresolved cases | Unnecessary abstention / answerable cases | Unauthorized writes / valid submissions |",
                        "|---|---|---:|---:|---:|",
                        *behaviors,
                        "",
                    ]
                )
            if matched:
                lines.extend(
                    [
                        "| Model | Paired comparison | Matched tasks | Correct before → after | Repaired | Regressed |",
                        "|---|---|---:|---:|---:|---:|",
                        *matched,
                        "",
                    ]
                )
            if cases:
                lines.extend(["### Observed discrepancies", "", *cases, ""])
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("export", "render"))
    parser.add_argument("--runs", type=Path, default=study.DEFAULT_OUT)
    parser.add_argument(
        "--tracks", choices=study.TRACKS, nargs="+", default=study.TRACKS
    )
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.operation == "export":
        archive = archive_runs(args.runs, args.tracks)
        study.save(args.archive, archive)
    else:
        archive = study.read(args.archive)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render(archive))


if __name__ == "__main__":
    main()
