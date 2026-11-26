"""Score local pilot outputs in a macOS sandbox and emit shareable records."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from run import BENCH, digest, jobs, name


def sandbox_grade(command, tmp, readable):
    """Use a fresh temporary home and deny network, secret files and repository writes."""
    paths = ["/System", "/usr", "/opt/homebrew", "/dev", "/Library", "/private/etc",
             "/private/var/db/timezone", str(tmp), *map(str, readable)]
    reads = " ".join("(subpath " + json.dumps(p) + ")" for p in paths)
    profile = f"""(version 1)
(allow default)
(deny network*)
(deny file-read-data (subpath "/Users") (subpath "/private/tmp") (subpath "/private/var/folders"))
(allow file-read-data {reads})
(deny file-write*)
(allow file-write* (subpath {json.dumps(str(tmp))}) (literal "/dev/null"))
"""
    env = {"HOME": str(tmp), "TMPDIR": str(tmp), "PATH": "/usr/bin:/bin",
           "LC_ALL": "C", "OPENBLAS_NUM_THREADS": "1", "XDG_CACHE_HOME": str(tmp / "cache")}
    run = subprocess.run(["/usr/bin/sandbox-exec", "-p", profile, *command], cwd=tmp,
                         env=env, capture_output=True, text=True, timeout=145)
    if run.returncode not in (0, 1) or not run.stdout.strip():
        raise RuntimeError("Evaluator infrastructure failed: " + run.stderr[-1500:])
    return json.loads(run.stdout)


def grade(job, work, external_python, cache):
    agent, task, rep, condition = job
    folder = work / name(job)
    record = json.loads((folder / "generation.json").read_text())
    if record["status"] != "submitted":
        return {**record, "passed": 0, "total": 1 if task.isdecimal() else 8, "checks": []}
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp).resolve()
        submission = tmp / ("solution.py" if task.isdecimal() else "analysis.py")
        shutil.copyfile(folder / "submission.py", submission)
        if digest(submission.read_bytes()) != record["submission_sha256"]:
            raise ValueError("Changed submission for " + name(job))
        if task.isdecimal():
            tool = BENCH / "external/ds1000.py"
            expected = tmp / "cache/sciskills" / cache.name
            expected.parent.mkdir(parents=True)
            shutil.copyfile(cache, expected)
            cmd = [str(external_python), "-I", str(tool), "score", task, str(tmp)]
            verdict = sandbox_grade(cmd, tmp, [tool, external_python.parent.parent.resolve()])
            return {**record, "passed": verdict["score"], "total": verdict["total"],
                    "checks": [{"check": "upstream", "passed": verdict["passed"]}]}
        tool = BENCH / "benchmark.py"
        cmd = [sys.executable, "-I", str(tool), "score", "--case", task,
               "--submission", str(submission), "--condition", condition, "--trial", str(rep),
               "--agent", agent, "--model", record["model"], "--elapsed-seconds",
               str(record["elapsed_seconds"])]
        if condition == "skill":
            cmd.extend(["--skill", record["skill"]])
        outcome = sandbox_grade(cmd, tmp, [tool])
        if outcome.get("case") != task or outcome.get("submission_sha256") != record["submission_sha256"]:
            raise RuntimeError("Native grader returned an invalid record")
        return {**record, "passed": outcome["passed"], "total": outcome["total"],
                "checks": outcome.get("checks", []),
                **({"grading_error": outcome["error"]} if "error" in outcome else {})}



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path)
    parser.add_argument("--external-python", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not sys.platform.startswith("darwin"):
        parser.error("This local scoring driver requires macOS sandbox-exec.")
    external = args.external_python.absolute()
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache = cache_root / "sciskills/ds1000-cddd24520f374c6cdf3497adf058467394f3cf0b.jsonl.gz"
    records = [grade(job, args.runs, external, cache) for job in jobs()]
    args.output.mkdir(exist_ok=True, parents=True)
    (args.output / "trials.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in records))
    protocol = json.loads((args.runs / "protocol.json").read_text())
    protocol["prompt_sha256"] = {f"{r['task']}/{r['condition']}": r["prompt_sha256"] for r in records}
    protocol["scored_utc"] = datetime.now(timezone.utc).isoformat()
    protocol["grader_sha256"] = {p.name: digest(p.read_bytes()) for p in [BENCH / "external/ds1000.py", BENCH / "benchmark.py"]}
    (args.output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    totals = defaultdict(Counter)
    for row in records:
        tally = totals[row["task"], row["agent"], row["condition"]]
        tally["passes"] += row["passed"] == row["total"]
        tally["runs"] += 1
    for key, tally in sorted(totals.items()):
        print(*key, f"{tally['passes']}/{tally['runs']}")


if __name__ == "__main__":
    main()
