"""Audit changes in submitted nanoindentation estimates after both models finish."""

import csv
import hashlib
import inspect
import io
import json
import math
import subprocess
import tarfile

from . import frontier, repair_trial, study

TASK = "nanoindentation-property-extraction"


def submitted_csv(case, row):
    context = row["participant_context"]
    docker = frontier._docker(context)
    if frontier._engine_id(context) != row["participant_engine"]:
        raise ValueError("Original participant engine is unavailable")
    container = frontier.command(
        *docker,
        "create",
        "--platform",
        frontier.platform(case),
        "--network",
        "none",
        "--entrypoint",
        "/bin/true",
        row["image"],
    ).stdout.strip()
    try:
        # Bound the Docker tar stream before it reaches memory or local disk.
        limit = 2_000_000 + 64 * 1024
        with subprocess.Popen(
            [*docker, "cp", container + ":/workspace/output/results.csv", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ) as copy:
            try:
                packed = subprocess.run(
                    ["head", "-c", str(limit + 1)],
                    stdin=copy.stdout,
                    capture_output=True,
                    check=True,
                    timeout=30,
                ).stdout
                if len(packed) > limit or copy.wait(timeout=5):
                    raise ValueError("Oversize or unreadable submitted CSV archive")
            finally:
                if copy.poll() is None:
                    copy.kill()
        with tarfile.open(fileobj=io.BytesIO(packed), mode="r:") as archive:
            members = archive.getmembers()
            if (
                len(members) != 1
                or not members[0].isfile()
                or members[0].name != "results.csv"
                or members[0].size > 2_000_000
            ):
                raise ValueError("Unexpected submitted CSV")
            stream = archive.extractfile(members[0])
            if stream is None:
                raise ValueError("Missing submitted CSV")
            data = stream.read()
    finally:
        frontier.command(*docker, "rm", container)
    return data


def estimates(data):
    result = {}
    for row in csv.DictReader(io.StringIO(data.decode("utf-8-sig"))):
        key = row["sample"], row["property"]
        value = float(row["value"])
        if key in result or not math.isfinite(value):
            raise ValueError("Ambiguous or non-finite estimate")
        result[key] = value
    return result


def compare_changes(entries, truth, spec_for):
    """Run inside the verifier. Return directions and tolerance decisions only."""
    import math

    output = []
    for sample, prop, values in entries:
        reference = truth[sample][prop]
        rule = spec_for(sample, prop)
        if (
            not math.isfinite(reference)
            or not math.isfinite(rule["tol"])
            or rule["tol"] <= 0
        ):
            raise ValueError("Invalid reference or tolerance")
        errors = [abs(v - reference) for v in values]
        if rule["mode"] == "rel":
            if reference == 0:
                raise ValueError("Invalid zero reference for relative tolerance")
            errors = [e / abs(reference) for e in errors]
        elif rule["mode"] != "abs":
            raise ValueError("Unknown tolerance mode")

        def direction(i, j):
            if values[i] == values[j]:
                return "unchanged"
            if abs(errors[j] - errors[i]) <= 0.001 * rule["tol"]:
                return "unresolved"
            return "closer" if errors[j] < errors[i] else "farther"

        output.append(
            {
                "within_tolerance": [e <= rule["tol"] for e in errors],
                "ordinary_vs_draft": direction(0, 1),
                "skill_vs_ordinary": direction(1, 2),
            }
        )
    return output


def audit(out):
    protocol, _, cases = repair_trial.validate_protocol(out)
    case = cases[TASK]
    evidence = study.read(study.HERE / "results/material-properties.json")
    if evidence["protocol_sha256"] != study.digest(repair_trial.PROTOCOL.read_text()):
        raise ValueError("Published evidence belongs to a different protocol")
    plan = {}
    for model in protocol["models"]:
        rows = {}
        public = repair_trial.assignment(
            out, TASK, model, protocol, validated_rows=rows
        )
        if not all(type(public[a].get("correct")) is bool for a in repair_trial.ARMS):
            raise ValueError(
                "Finish all six original grades before the supplemental audit"
            )
        if public["draft"]["draft_sha256"] != evidence["models"][model]["draft_sha256"]:
            raise ValueError("The first draft differs from the published audit")
        plan[model] = rows

    placement = study.read(out / "frontier/execution-contexts" / (TASK + ".json"))
    control = study.read(frontier._scoped_receipt(case, placement["context"]))
    if (
        control.get("commit") != frontier.MANIFEST["commit"]
        or control.get("task") != TASK
        or control["participant_context"] != placement["context"]
        or control["participant_engine"] != placement["engine"]
        or control["tests_image"] != evidence["verifier_image"]
        or not frontier.live_control(case, control)
    ):
        raise ValueError("Original positive and negative controls are required")

    program = (
        inspect.getsource(compare_changes)
        + """
import json, runpy, sys
grader = runpy.run_path('/tests/test_nanoindentation.py')
print(json.dumps(compare_changes(json.loads(sys.argv[1]), grader['_truth'](), grader['_spec_for'])))
"""
    )
    result = {}
    verifier = control["verifier_context"]
    with frontier.temporary_container(
        case, verifier=True, context=verifier, image_id=control["tests_image"]
    ) as target:
        for model, rows in plan.items():
            data = [submitted_csv(case, rows[a]) for a in repair_trial.ARMS]
            fingerprints = {
                a: hashlib.sha256(content).hexdigest()
                for a, content in zip(repair_trial.ARMS, data)
            }
            if fingerprints != evidence["models"][model]["csv_sha256"]:
                raise ValueError(
                    "Submitted files differ from the six completed, published arms"
                )
            values = [estimates(content) for content in data]
            if not values[0] or not (
                values[0].keys() == values[1].keys() == values[2].keys()
            ):
                raise ValueError("The submitted property sets differ")
            entries = []
            for sample, prop in sorted(values[0]):
                reported = [v[(sample, prop)] for v in values]
                if len(set(reported)) > 1:
                    entries.append([sample, prop, reported])
            response = frontier._root_exec(
                target,
                "python3",
                "-c",
                program,
                json.dumps(entries, allow_nan=False),
                context=verifier,
                check=False,
            )
            if response.returncode:
                raise RuntimeError("The isolated official property evaluator failed")
            verdicts = json.loads(response.stdout)
            if not isinstance(verdicts, list) or len(verdicts) != len(entries):
                raise ValueError("Invalid diagnostic result count")
            changes = []
            for (sample, prop, reported), verdict in zip(entries, verdicts):
                flags = verdict["within_tolerance"]
                directions = [
                    verdict[k] for k in ("ordinary_vs_draft", "skill_vs_ordinary")
                ]
                if (
                    len(flags) != 3
                    or any(type(v) is not bool for v in flags)
                    or any(
                        v not in ("closer", "farther", "unchanged", "unresolved")
                        for v in directions
                    )
                ):
                    raise ValueError("Invalid diagnostic verdict")
                changes.append(
                    {
                        "sample": sample,
                        "property": prop,
                        "submitted": reported,
                        "within_tolerance": flags,
                        "ordinary_vs_draft": directions[0],
                        "skill_vs_ordinary": directions[1],
                    }
                )
            result[model] = {
                "draft_sha256": study.draft_identity(rows["draft"]),
                "csv_sha256": fingerprints,
                "rows": len(values[0]),
                "changed": changes,
            }
    return {
        "task": TASK,
        "protocol_sha256": study.digest(repair_trial.PROTOCOL.read_text()),
        "verifier_image": control["tests_image"],
        "arm_order": list(repair_trial.ARMS),
        "models": result,
    }


if __name__ == "__main__":
    print(json.dumps(audit(study.DEFAULT_OUT), indent=2))
