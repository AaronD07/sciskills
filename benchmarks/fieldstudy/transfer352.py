"""Check archived problem 352 completions on fresh summary statistics (macOS)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile

STUDY = Path(__file__).resolve().parents[1] / "study"
sys.path.insert(0, str(STUDY))
from score import sandbox_grade

# Each case varies the supplied means, variances and sample sizes. The first
# has equal means and a known two-sided p-value of one.
CASES = [(4, 1, 8, 4, 7, 13), (-2, 4, 19, 1.4, 0.6, 7), (1, 0.8, 12, 1.3, 4.1, 37)]
DRIVER = """
import contextlib, io, json, math, numpy as np, scipy.stats
from pathlib import Path
source = Path("submission.py").read_text()
checks = []
for amean, avar, anobs, bmean, bvar, bnobs in json.loads(Path("cases.json").read_text()):
    expected = scipy.stats.ttest_ind_from_stats(amean, math.sqrt(avar), anobs,
        bmean, math.sqrt(bvar), bnobs, equal_var=False).pvalue
    inputs = dict(np=np, scipy=scipy, amean=amean, avar=avar, anobs=anobs,
                  bmean=bmean, bvar=bvar, bnobs=bnobs)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(source, "submission.py", "exec"), inputs)
        checks.append(math.isclose(inputs["p_value"], expected, abs_tol=1e-5, rel_tol=0))
    except Exception:
        checks.append(False)
print(json.dumps(checks))
"""


def run(python):
    folder = STUDY / "results"
    sources = {r["sha256"]: r["source"] for r in map(json.loads, (folder / "submissions.jsonl").read_text().splitlines())}
    rows = []
    for record in map(json.loads, (folder / "trials.jsonl").read_text().splitlines()):
        if record["task"] != "352":
            continue
        key = record["submission_sha256"]
        source = sources[key]
        if hashlib.sha256(source.encode()).hexdigest() != key:
            raise ValueError("Archived submission hash differs")
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory).resolve()
            (tmp / "cases.json").write_text(json.dumps(CASES))
            (tmp / "submission.py").write_text(source)
            checks = sandbox_grade([str(python), "-I", "-c", DRIVER], tmp, [python.parent.parent.resolve()])
        rows.append({k: record[k] for k in ("agent", "condition", "repetition", "submission_sha256")} | {"checks": checks})
    if len(rows) != 12:
        raise ValueError("Expected 12 archived submissions")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-python", required=True, type=Path)
    args = parser.parse_args()
    for row in run(args.external_python.absolute()):
        print(json.dumps(row, sort_keys=True))
