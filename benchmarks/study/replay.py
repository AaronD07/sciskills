"""Verify the published submissions and reproduce the stored per-check outcomes."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from run import BENCH, STUDY, digest, jobs, name, prompt
from score import grade


def replay(external_python, results):
    records = [json.loads(line) for line in (results / "trials.jsonl").read_text().splitlines()]
    sources = {}
    for line in (results / "submissions.jsonl").read_text().splitlines():
        item = json.loads(line)
        if digest(item["source"].encode()) != item["sha256"]:
            raise ValueError("Submission content failed integrity check")
        sources[item["sha256"]] = item["source"]
    protocol = json.loads((results / "protocol.json").read_text())
    for tool in (BENCH / "benchmark.py", BENCH / "external/ds1000.py"):
        if digest(tool.read_bytes()) != protocol["grader_sha256"][tool.name]:
            raise ValueError(f"Grader differs from published version: {tool.name}")
    cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache = cache / "sciskills/ds1000-cddd24520f374c6cdf3497adf058467394f3cf0b.jsonl.gz"
    schedule = list(jobs())
    if len(records) != len(schedule) or protocol["order"] != list(map(name, schedule)):
        raise ValueError("Incomplete or different schedule")
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        prompts = {}
        for job, record in zip(schedule, records):
            if tuple(record[k] for k in ("agent", "task", "repetition", "condition")) != job:
                raise ValueError("Record disagrees with schedule")
            agent, task, rep, condition = job
            key = (task, condition)
            if key not in prompts:
                prompts[key] = digest(prompt(*key).encode())
            if prompts[key] != record["prompt_sha256"]:
                raise ValueError("Current prompt differs from measured prompt")
            folder = root / name(job)
            folder.mkdir()
            (folder / "generation.json").write_text(json.dumps(record))
            if record["status"] == "submitted":
                (folder / "submission.py").write_text(sources[record["submission_sha256"]])
            actual = grade(job, root, external_python, cache)
            for field in ("passed", "total", "checks"):
                if actual[field] != record[field]:
                    raise ValueError(f"Different {field} for {name(job)}")
    print(f"Matched all {len(records)} recorded runs and per-check outcomes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-python", required=True, type=Path)
    parser.add_argument("--results", default=STUDY / "results", type=Path)
    args = parser.parse_args()
    replay(args.external_python.absolute(), args.results)
