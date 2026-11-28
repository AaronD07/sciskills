"""Export anonymized results and render matched, same-draft comparisons offline."""

import argparse
from collections import Counter, defaultdict
import json
import math
from pathlib import Path

from . import everyday, frontier, study

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
    "participant_host_oom",
    "pending_engine_requalification",
    "verifier_killed",
    "unsupported_artifact",
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
    return (
        value if isinstance(value, str) and value in KNOWN_STATUS else "unknown_error"
    )


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
        pytest_outcomes = score.get("pytest_outcomes") or frontier._pytest_counts(
            score.get("verifier_tail", "")
        )
        summary["pytest_outcomes"] = {
            k: n
            for k, n in pytest_outcomes.items()
            if k
            in ("passed", "failed", "skipped", "error", "errors", "xfailed", "xpassed")
            and type(n) is int
        }
        summary["missing_artifacts"] = len(score.get("missing", []))
    return summary


def _docker_identity(record, role="participant"):
    """Keep context and engine distinct: a rebuilt daemon can reuse a context name."""
    identity = {}
    for field in ("context", "engine"):
        value = record.get(role + "_" + field)
        if isinstance(value, str) and value:
            identity[field] = field + "-" + study.digest(field + "/" + value)[:16]
    return identity


def _controls(folder, track, task, phase):
    main = folder / (task + ".json")
    paths = ([main] if main.is_file() else []) + sorted(
        (folder / "contexts").glob("*/" + task + ".json")
    )
    contexts = {}
    for path in paths:
        receipt = study.read(path)
        if receipt.get("task", task) != task or receipt.get("phase", phase) != phase:
            continue
        if (
            track == "frontier"
            and receipt.get("commit", frontier.MANIFEST["commit"])
            != frontier.MANIFEST["commit"]
        ):
            continue
        participant = _docker_identity(receipt)
        negative = (receipt.get("negative") or {}).get("correct")
        positive = (receipt.get("positive") or {}).get("correct")
        ready = receipt.get("ready") is True and negative is False
        if track == "frontier":
            ready = (
                ready
                and positive is True
                and (receipt.get("positive") or {}).get("reward", 1) == 1
            )
        # The runtime gives this participant's scoped receipt precedence over the main copy.
        key = participant.get("context") or participant.get("engine") or "legacy"
        contexts[key] = {
            "participant": participant,
            "verifier": _docker_identity(receipt, "verifier"),
            "ready": ready,
            "negative_correct": negative if type(negative) is bool else None,
            "positive_correct": positive if type(positive) is bool else None,
        }
    if not contexts:
        return None
    entries = [contexts[k] for k in sorted(contexts)]
    chosen = next((r for r in entries if r["ready"]), entries[0])
    return {k: chosen[k] for k in ("ready", "negative_correct", "positive_correct")} | {
        "any_context_ready": any(r["ready"] for r in entries),
        "contexts": entries,
        "used_contexts": [],
    }


def _match_controls(control, participant):
    if (
        not participant
        or set(participant) != {"context", "engine"}
        or not all(participant.values())
    ):
        return []
    return [
        r
        for r in (control or {}).get("contexts", [])
        if r["participant"] == participant
    ]


def _verified(control):
    return (
        control.get("ready") is True
        and control.get("negative_correct") is False
        and control.get("positive_correct") is True
    )


# A retry or later infrastructure adjudication can save the same session in several places.
_HISTORY_DIRS = (
    "failed-attempts",
    "discarded-retries",
    "interrupted-network-or-host",
    "host-memory-incidents",
    "conflicting-client-permissions",
)


def _attempt_key(row):
    """Local-only identity; receipts and their digests never enter the published export."""
    session = row.get("session") or {}
    if row.get("attempt_id") or session.get("attempt_id"):
        receipt = {"attempt": row.get("attempt_id") or session["attempt_id"]}
    elif row.get("incident_sha256"):
        receipt = {"incident": row["incident_sha256"]}
    elif number(session.get("elapsed_seconds")):
        # Adjudication may recover a missing reply or change status on the same tool trace.
        receipt = {k: session.get(k) for k in ("model", "elapsed_seconds", "calls")}
    elif session:
        receipt = {
            k: v for k, v in session.items() if k not in ("status", "subscription")
        }
    else:
        receipt = {
            k: v for k, v in row.items() if k not in ("score", "reason", "recovery")
        }
    return study.digest(study.encode(receipt))


def _history_paths(directory):
    paths = defaultdict(list)
    for source in _HISTORY_DIRS:
        for path in sorted((directory / source).rglob("*.json")):
            paths[path.name].append((source, path))
    return paths


def _history_for(identity, paths, current):
    reasons = defaultdict(set)
    current_key = _attempt_key(current) if current else None
    if current and current["status"] != "submitted":
        reasons[current_key].add(safe_status(current["status"]))
    for source, path in paths:
        record = study.read(path)
        if any(record.get(k) != v for k, v in identity.items()):
            raise ValueError(
                "Archived attempt identity differs from its scheduled task"
            )
        if source == "host-memory-incidents":
            reason = "participant_host_oom"
        elif source == "conflicting-client-permissions":
            reason = "conflicting_client_permissions"
        else:
            reason = safe_status(record.get("status"))
        reasons[_attempt_key(record)].add(reason)
    # Prefer confirmed causes to provisional CLI errors when both refer to one attempt.
    priorities = (
        "participant_host_oom",
        "conflicting_client_permissions",
        "tool_unavailable",
        "quota_exhausted",
        "authentication_error",
        "pending_engine_requalification",
        "cli_error",
    )
    counts = Counter()
    for key, labels in reasons.items():
        reason = next((s for s in priorities if s in labels), sorted(labels)[0])
        relationship = (
            "same_attempt"
            if key == current_key
            else "other_attempt"
            if current
            else "no_current_record"
        )
        counts[reason, relationship] += 1
    return [
        {**identity, "reason": reason, "current_record": relationship, "count": n}
        for (reason, relationship), n in sorted(counts.items())
    ]


def archive_runs(root, tracks=study.TRACKS):
    """Build an allowlisted archive from local primary records, independent of wall time."""
    archive = {"schema_version": 1, "tracks": {}, "rows": [], "attempt_history": []}
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
            for phase, ids in design["tasks"].items():
                for task in sorted(ids):
                    control = _controls(
                        root / (track + "-controls"), track, task, phase
                    )
                    if control:
                        frozen["controls"][task] = control
        archive["tracks"][track] = frozen
        for phase, ids in sorted(frozen["tasks"].items()):
            ev = (
                {c["id"]: c for c in everyday.cases(phase)}
                if track == "everyday"
                else {}
            )
            observed = {p.name for p in (directory / phase).glob("*.json")}
            history = _history_paths(directory / phase)
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
                        identity = {
                            "track": track,
                            "phase": phase,
                            "task": task,
                            "model": model,
                            "arm": arm,
                        }
                        path = directory / phase / name
                        row = study.read(path) if name in observed else None
                        if row and any(row[k] != v for k, v in identity.items()):
                            raise ValueError(f"Session identity mismatch for {name}")
                        if name in history or (row and row["status"] != "submitted"):
                            archive["attempt_history"].extend(
                                _history_for(identity, history.get(name, []), row)
                            )
                        if row is None:
                            continue
                        observed.remove(name)
                        grade = public_row(row, draft, ev.get(task))
                        if track == "frontier":
                            participant = _docker_identity(row)
                            if participant:
                                grade["participant"] = participant
                            if phase == "holdout" and row["status"] == "submitted":
                                control = frozen["controls"].get(task)
                                matching = _match_controls(control, participant)
                                qualified = any(_verified(r) for r in matching)
                                if (
                                    control
                                    and participant not in control["used_contexts"]
                                ):
                                    control["used_contexts"].append(participant)
                                if "correct" in grade and not qualified:
                                    grade = {
                                        "outcome": "infrastructure",
                                        "reason": "unverified_participant_control",
                                        "participant": participant,
                                    }
                                grade["participant_control_verified"] = qualified
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
                        archive["rows"].append({**identity, **grade})
                        if arm == "draft":
                            draft = row
            if observed:
                raise ValueError(
                    f"Unexpected sessions outside frozen design: {sorted(observed)}"
                )
        for control in frozen.get("controls", {}).values():
            used = control["used_contexts"]
            if used:
                control["ready"] = all(
                    any(r["ready"] for r in _match_controls(control, p)) for p in used
                )
                # Task-level control evidence must describe engines used for those results.
                relevant = [r for p in used for r in _match_controls(control, p)]
                for field in ("negative_correct", "positive_correct"):
                    values = {r[field] for r in relevant}
                    control[field] = (
                        values.pop()
                        if len(values) == 1
                        and all(_match_controls(control, p) for p in used)
                        else None
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
        if r["track"] == "frontier" and r["phase"] == "holdout" and "correct" in r:
            control = archive["tracks"]["frontier"].get("controls", {}).get(r["task"])
            if not any(
                _verified(c) for c in _match_controls(control, r.get("participant"))
            ):
                # Older exports can carry a score without binding it to a tested engine.
                r = {
                    **r,
                    "outcome": "infrastructure",
                    "reason": "unverified_participant_control",
                }
                r.pop("correct")
        by_group[r["track"], r["phase"], r["model"], r["task"]][r["arm"]] = r
    for track, design in sorted(archive["tracks"].items()):
        for phase in ("dev", "holdout"):
            lines.extend([f"## {track.capitalize()} {phase}", ""])
            if "attempt_history" in archive:
                history = [
                    r
                    for r in archive["attempt_history"]
                    if r["track"] == track and r["phase"] == phase
                ]
                if history:
                    totals = Counter()
                    for attempt in history:
                        totals[
                            attempt["model"],
                            attempt["arm"],
                            attempt["reason"],
                            attempt["current_record"],
                        ] += attempt["count"]
                    lines.extend(
                        [
                            "### Distinct recorded interruptions and exclusions",
                            "",
                            "Each attempt appears once, including exclusions whose replacement has yet to return. A recovered attempt can also have a current result. These counts do not enter the task accuracy denominators.",
                            "",
                            "| Model | Arm | Recorded reason | Distinct recorded attempts | Same attempt as current row | Different current row | No current row |",
                            "|---|---|---|---:|---:|---:|---:|",
                        ]
                    )
                    for model, arm, reason in sorted({k[:3] for k in totals}):
                        values = [
                            totals[model, arm, reason, r]
                            for r in (
                                "same_attempt",
                                "other_attempt",
                                "no_current_record",
                            )
                        ]
                        lines.append(
                            f"| {model} | {arm} | {reason} | {sum(values)} | {values[0]} | {values[1]} | {values[2]} |"
                        )
                    lines.append("")
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
                comparisons = []
                for task in sorted(design["tasks"][phase]):
                    metadata = design["controls"].get(task, {})
                    engines = metadata.get("contexts", [])
                    if not any(e["participant"] for e in engines) and not metadata.get(
                        "used_contexts"
                    ):
                        continue
                    for engine in engines:
                        participant = engine["participant"]
                        used = any(
                            engine in _match_controls(metadata, p)
                            for p in metadata["used_contexts"]
                        )
                        name = ", ".join(participant.values()) or "unrecorded"
                        verifier = (
                            ", ".join(engine["verifier"].values()) or "unrecorded"
                        )
                        comparisons.append(
                            f"| `{task}` | {name} | {verifier} | {'ready' if engine['ready'] else 'failed'} | {'yes' if used else '—'} |"
                        )
                    for participant in metadata.get("used_contexts", []):
                        if not _match_controls(metadata, participant):
                            name = ", ".join(participant.values()) or "unrecorded"
                            comparisons.append(
                                f"| `{task}` | {name} | unrecorded | missing | yes |"
                            )
                if comparisons:
                    lines.extend(
                        [
                            "Control names and engine identifiers are pseudonymous. Each frontier holdout score requires a recorded participant context and engine with successful negative and positive controls. Development scores can include older submissions lacking engine metadata.",
                            "",
                            "| Task | Participant | Verifier | Reference controls | Recorded holdout use |",
                            "|---|---|---|---|---|",
                            *comparisons,
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
