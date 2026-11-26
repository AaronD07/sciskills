"""Audit every trial, optionally replaying the model's local Python calls."""
import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median
import tempfile

import python_tool
import study


def trial_id(row):
    return "-".join(str(row[k]) for k in ("agent", "split", "repetition", "condition"))


def archive(private, results):
    """Archive only submitted Python snippets and their digests, leaving CLI logs private."""
    sources = {}
    for row in load_trials(results):
        path = private / trial_id(row) / "calls.jsonl"
        calls = [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []
        if [study.digest(call["code"]) for call in calls] != [c["code_sha256"] for c in row["calls"]]:
            raise ValueError("Private call history disagrees with trial receipts")
        for call in calls:
            sources[study.digest(call["code"])] = call["code"]
    with (results / "python-calls.jsonl").open("x") as fp:
        for sha, code in sorted(sources.items()):
            fp.write(study.normalized({"code_sha256": sha, "source": code}) + "\n")


def load_trials(results):
    return [json.loads(s) for s in (results / "trials.jsonl").read_text().splitlines()]


def audit(results, replay):
    protocol = json.loads((results / "protocol.json").read_text())
    rows = load_trials(results)
    if Counter(map(trial_id, rows)) != Counter(map(trial_id, protocol["schedule"])):
        raise ValueError("Missing or duplicate trial")
    if protocol["tool_sha256"] != study.digest((study.HERE / "python_tool.py").read_text()):
        raise ValueError("Calculator runtime differs from measured version")
    library = {}
    for line in (results / "python-calls.jsonl").read_text().splitlines():
        entry = json.loads(line)
        sha = entry["code_sha256"]
        if sha != study.digest(entry["source"]):
            raise ValueError("Unexpected Python source hash")
        library[sha] = entry["source"]
    for row in rows:
        files, gold = study.materials(row["split"], row["condition"])
        frozen = protocol["inputs"][row["split"] + "." + row["condition"]]
        if (row["files"] != frozen["files"] or study.hashes(files) != frozen["files"]
            or study.digest(study.normalized(gold)) != frozen["gold_sha256"]
            or study.digest(row["answer"]) != row["answer_sha256"]
            or row["model"] != protocol["models"][row["agent"]]):
            raise ValueError("Inputs, answer or model differ from record")
        score = study.grade(row["answer"] if row["status"] == "submitted" else "", gold)
        if any(row[k] != v for k, v in score.items()):
            raise ValueError("Field grade mismatch")
        for call in row["calls"]:
            if call["code_sha256"] not in library:
                raise ValueError("Missing submitted code")
        if replay:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp).resolve()
                for name, body in files.items():
                    (work / name).write_text(body)
                for call in row["calls"]:
                    status, _, observed = python_tool.execute(library[call["code_sha256"]], work)
                    if status != call["exit_status"] or observed != call["helper_functions"]:
                        raise ValueError(f"Different calculator execution in {trial_id(row)}")
                if study.answer_text(work) != row["answer"]:
                    raise ValueError(f"Different final answer in {trial_id(row)}")
    return rows


def stats(rows):
    groups = defaultdict(list)
    for row in rows:
        for group in ("all", row["agent"], row["split"]):
            groups[group].append(row)
    report = {}
    for group, members in groups.items():
        cells = {}
        for arm in ("baseline", "skill"):
            arm_rows = [r for r in members if r["condition"] == arm]
            checks = [sum(r["checks"].values()) for r in arm_rows]
            counts = [len(r["calls"]) for r in arm_rows]
            selectors = sum(any("select" in c["helper_functions"] for c in r["calls"]) for r in arm_rows)
            cells[arm] = {"n": len(checks), "full": sum(r["full_pass"] for r in arm_rows),
                          "correct_fields": sum(checks), "total_fields": sum(len(r["checks"]) for r in arm_rows),
                          "median_seconds": round(median(r["elapsed_seconds"] for r in arm_rows), 2),
                          "python_calls": sum(counts), "runs_using_helper_select": selectors,
                          "status": dict(Counter(r["status"] for r in arm_rows))}
        report[group] = cells
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("results", type=Path)
    ap.add_argument("--archive-private", type=Path, help="Export submitted Python source before checking")
    ap.add_argument("--replay", action="store_true", help="Run all snippets again in isolated local Python")
    opts = ap.parse_args()
    if opts.archive_private:
        archive(opts.archive_private, opts.results)
    data = audit(opts.results, opts.replay)
    print(json.dumps(stats(data), indent=2))
