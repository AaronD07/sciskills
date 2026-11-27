"""Export the paired results and independently replay their delivered artifacts."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path

if __package__:
    from . import trial
else:
    import trial


def interventions(work, modes):
    for mode in modes:
        for phase in ("dev", "holdout"):
            for case in trial.adapter(mode).cases(phase):
                for model in trial.runner.MODELS:
                    original = case["files"]
                    draft = None
                    for arm in (
                        "draft",
                        *trial.ARMS,
                        *(a + "-repeat" for a in trial.ARMS),
                    ):
                        path = trial.record(work, mode, phase, case, model, arm)
                        if not path.is_file():
                            continue
                        r = trial.read(path)
                        failed = path.parent / "infrastructure-attempts" / path.name
                        if failed.exists():
                            r["retry_of"] = trial.read(failed)["status"]
                        if arm == "draft":
                            draft = r
                        inherited = (
                            original
                            if arm == "draft"
                            else trial.runner.review_files(original, draft)
                        )
                        files = {**inherited, **r["artifacts"]}
                        for name in r["deleted"]:
                            files.pop(name, None)
                        # Only submitted programs and answer artifacts are needed by these graders.
                        submission = {
                            n: v
                            for n, v in files.items()
                            if (n == "answer.json" or n.endswith(".py"))
                            and not n.startswith("original_packet/")
                        }
                        yield case, r, submission, trial.digest(trial.encode(draft))


def expected_keys(protocol, rows):
    by_key = {
        (r["mode"], r["phase"], r["case"], r["client"], r["arm"]): r for r in rows
    }
    expected = set()
    for mode, suite in protocol["suites"].items():
        for phase, split in suite["splits"].items():
            if phase == "holdout" and mode not in protocol["qualified"]:
                continue
            for case_id in split:
                for model in suite["models"]:
                    group = (mode, phase, case_id, model)
                    key = (*group, "draft")
                    expected.add(key)
                    draft = by_key.get(key)
                    if draft is None or draft["status"] != "submitted":
                        continue
                    score = draft["initial_score"] or {}
                    selected = (
                        draft["strict_eligible"]
                        and score.get("valid")
                        and not score["correct"]
                    )
                    if phase == "holdout" or selected:
                        expected.update((*group, arm) for arm in trial.ARMS)
                    if phase == "holdout" and selected:
                        expected.update((*group, arm + "-repeat") for arm in trial.ARMS)
    return expected


def check_schedule(protocol, rows):
    expected = expected_keys(protocol, rows)
    observed = {(r["mode"], r["phase"], r["case"], r["client"], r["arm"]) for r in rows}
    if expected != observed or len(observed) != len(rows):
        raise ValueError(f"Missing or extra session(s): {sorted(expected ^ observed)}")


def grade_once(work, fingerprint, key, inputs):
    """Cache only local adjudication. Replay always executes the archived artifacts afresh."""
    case_id, submission_id = key
    path = work / "adjudication" / fingerprint / case_id / (submission_id + ".json")
    if path.is_file():
        return trial.read(path)
    result = trial.grade(*inputs)
    trial.save(path, result)
    return result


def export(work, output, modes):
    output.mkdir(parents=True, exist_ok=True)
    scores, artifacts, drafts, reviews = [], {}, {}, {}
    rows = list(interventions(work, modes))
    jobs = {}
    for c, r, files, _ in rows:
        if r["status"] == "submitted" and c["mode"] != "contest":
            key = (c["id"], trial.digest(trial.encode(files)))
            jobs[key] = c, files
    grader_files = [
        trial.HERE / name
        for name in ("trial.py", "programming.py", "statistics.py", "runtime.py")
    ]
    grader_files.extend(trial.HERE / (m + ".py") for m in modes)
    grader_files.append(trial.HERE.parent / "ledger-replay/python_tool.py")
    fingerprint = trial.digest(
        "".join(trial.digest(f.read_text()) for f in sorted(set(grader_files)))
    )
    with ThreadPoolExecutor(5) as pool:
        grades = dict(
            zip(
                jobs,
                pool.map(lambda k: grade_once(work, fingerprint, k, jobs[k]), jobs),
            )
        )
    for c, r, files, draft_digest in rows:
        fid = trial.digest(trial.encode(files))
        artifacts[fid] = files
        if r["arm"] == "draft":
            drafts[draft_digest] = r
        else:
            reviews["/".join((r["phase"], c["id"], r["client"], r["arm"]))] = {
                "calls": r["calls"],
                "reply": r["reply"],
                "elapsed_seconds": r["elapsed_seconds"],
                "draft_sha256": draft_digest,
            }
        judged = r["score"] if c["mode"] == "contest" else grades.get((c["id"], fid))
        scores.append(
            {
                "mode": c["mode"],
                "phase": r["phase"],
                "case": c["id"],
                "family": c["family"],
                "client": r["client"],
                "model": r["model"],
                "arm": r["arm"],
                "status": r["status"],
                "score": judged if r["status"] == "submitted" else None,
                "initial_score": r["score"],
                "retry_of": r.get("retry_of"),
                "draft_sha256": draft_digest,
                "files_sha256": fid,
                "strict_eligible": c.get("strict_eligible", True),
                "decision_eligible": c.get("decision_eligible", True),
            }
        )
    (output / "scores.jsonl").write_text(
        "".join(trial.encode(r) + "\n" for r in scores)
    )
    (output / "submissions.json.gz").write_bytes(
        gzip.compress(trial.encode(artifacts).encode(), mtime=0)
    )
    (output / "drafts.json.gz").write_bytes(
        gzip.compress(trial.encode(drafts).encode(), mtime=0)
    )
    (output / "reviews.json.gz").write_bytes(
        gzip.compress(trial.encode(reviews).encode(), mtime=0)
    )
    files = [
        p
        for p in trial.HERE.rglob("*")
        if p.is_file()
        and "results" not in p.parts
        and (
            p.suffix == ".py"
            or p.name in ("manifest.json", "key_audit.json", "requirements.txt")
        )
    ]
    files += [
        trial.ROOT / "benchmarks" / subpath
        for subpath in (
            "paired_review/runner.py",
            "paired_review/grading.py",
            "ledger-replay/python_tool.py",
            "ledger-replay/study.py",
            "fieldstudy/runner.py",
        )
    ]
    protocol = {
        "subscription": trial.read(work / "subscription.json"),
        "rows": len(scores),
        "archives": {
            name: hashlib.sha256((output / name).read_bytes()).hexdigest()
            for name in (
                "scores.jsonl",
                "submissions.json.gz",
                "drafts.json.gz",
                "reviews.json.gz",
            )
        },
        "suites": {m: trial.read(work / m / "protocol.json") for m in modes},
        "qualified": [
            m
            for m in modes
            if len(trial.qualifying_errors(work, m, trial.adapter(m).cases("dev"))) >= 2
        ],
        "implementation": {
            str(p.relative_to(trial.ROOT)): trial.digest(p.read_text()) for p in files
        },
    }
    check_schedule(protocol, scores)
    trial.save(output / "protocol.json", protocol)
    return scores


def paired(rows):
    groups = defaultdict(dict)
    for r in rows:
        groups[(r["phase"], r["mode"], r["case"], r["client"])][r["arm"]] = r
    counts = defaultdict(Counter)
    for (phase, mode, _, _), arms in groups.items():
        draft = arms["draft"]
        initial = draft["score"]
        summary = counts[phase, mode]
        summary["drafts"] += 1
        if initial is None or not initial["valid"]:
            summary["unavailable_or_invalid_draft"] += 1
        if initial and initial["correct"]:
            summary["draft_correct"] += 1
        if not draft["strict_eligible"]:
            summary["disputed_draft"] += 1
            continue
        if initial is None or not initial["valid"]:
            for arm in trial.ARMS:
                end = arms.get(arm, {}).get("score")
                if end and end["correct"]:
                    summary[arm + "_recovered_invalid_draft"] += 1
            continue
        for suffix in ("", "-repeat"):
            if suffix and (phase != "holdout" or initial["correct"]):
                continue
            if phase == "dev" and initial["correct"]:
                continue
            for family in trial.ARMS:
                arm = family + suffix
                treatment = arms.get(arm)
                summary[arm + "_expected"] += 1
                score = treatment["score"] if treatment else None
                if treatment:
                    summary[arm + "_attempts"] += 1
                if score is None or not score["valid"]:
                    summary[arm + "_missing_or_invalid"] += 1
                if not initial["correct"]:
                    summary[arm + "_opportunities"] += 1
                    if score and score["correct"]:
                        summary[arm + "_repairs"] += 1
                    control = arms.get("ordinary" + suffix, {}).get("score")
                    if (
                        family != "ordinary"
                        and control
                        and score
                        and control["valid"]
                        and score["valid"]
                    ):
                        summary[arm + "_complete_pairs"] += 1
                        if score["correct"] and not control["correct"]:
                            summary[arm + "_only"] += 1
                        if control["correct"] and not score["correct"]:
                            summary["ordinary_only_vs_" + arm] += 1
                elif score is not None and not score["correct"]:
                    summary[arm + "_regressions"] += 1
    return {f"{k[0]}/{k[1]}": dict(v) for k, v in counts.items()}


def replay(output, scorer=trial.grade):
    protocol = trial.read(output / "protocol.json")
    for name, expected in protocol["archives"].items():
        if hashlib.sha256((output / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Archive changed: {name}")
    drafts = json.loads(gzip.decompress((output / "drafts.json.gz").read_bytes()))
    artifacts = json.loads(
        gzip.decompress((output / "submissions.json.gz").read_bytes())
    )
    rows = [
        json.loads(line) for line in (output / "scores.jsonl").read_text().splitlines()
    ]
    check_schedule(protocol, rows)
    keys = {(r["mode"], r["phase"], r["case"], r["client"], r["arm"]) for r in rows}
    if not rows or len(keys) != len(rows) or len(rows) != protocol["rows"]:
        raise ValueError("Incomplete or duplicate rows")
    for r in rows:
        draft = drafts[r["draft_sha256"]]
        if trial.digest(trial.encode(draft)) != r["draft_sha256"] or (
            draft["phase"],
            draft["case"],
            draft["client"],
        ) != (r["phase"], r["case"], r["client"]):
            raise ValueError("Incorrect paired draft")
    cases = {
        c["id"]: c
        for mode, phase in {(r["mode"], r["phase"]) for r in rows}
        for c in trial.adapter(mode).cases(phase)
    }
    jobs = {}
    for r in rows:
        fid = r["files_sha256"]
        files = artifacts[fid]
        if trial.digest(trial.encode(files)) != fid:
            raise ValueError("Corrupt submission")
        if r["status"] == "submitted":
            jobs[(r["case"], fid)] = (cases[r["case"]], files)
    with ThreadPoolExecutor(6) as pool:
        verified = dict(zip(jobs, pool.map(lambda item: scorer(*item), jobs.values())))
    for r in rows:
        expected = (
            verified.get((r["case"], r["files_sha256"]))
            if r["status"] == "submitted"
            else None
        )
        if r["score"] != expected:
            raise ValueError(f"Score differs: {r['case']} {r['client']} {r['arm']}")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["export", "replay"])
    parser.add_argument(
        "--work", type=Path, default=trial.ROOT / "benchmark-runs/public-hard"
    )
    parser.add_argument("--output", type=Path, default=trial.HERE / "results")
    parser.add_argument(
        "--modes", nargs="+", choices=trial.SPECIALIST, default=list(trial.SPECIALIST)
    )
    args = parser.parse_args()
    observations = (
        export(args.work, args.output, args.modes)
        if args.action == "export"
        else replay(args.output)
    )
    print(json.dumps(paired(observations), indent=2, sort_keys=True))
