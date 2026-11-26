"""Compare a post-study static check with previously observed replacement errors."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "skills/test-fresh-inputs"))
from check_inputs import find_overwrites


NAMES = {
    352: {"amean", "avar", "anobs", "bmean", "bvar", "bnobs"},
    108: {"df1", "df2"},
    411: {"a", "low_index", "high_index"},
}


def read(root):
    return [json.loads(line) for line in root.read_text().splitlines()]


def compare():
    old = HERE.parent / "study/results"
    src = {r["sha256"]: r["source"] for r in read(old / "submissions.jsonl")}
    failed_fresh = {
        r["submission_sha256"]
        for r in read(HERE.parent / "fieldstudy/transfer352.jsonl")
        if not all(r["checks"])
    }
    records = []
    for row in read(old / "trials.jsonl"):
        if row["task"] == "352":
            key = row["submission_sha256"]
            records.append((352, key, src[key], key in failed_fresh))
    # The file-edit report identifies both fixed-data failures on 411 and the
    # unrelated source-form failures on 108. Use those prior manual labels.
    copied = {("claude", 411, "baseline", 1), ("claude", 411, "skill", 2)}
    for row in read(HERE / "file-results/trials.jsonl"):
        label = (
            row["agent"],
            row["task"],
            row["condition"],
            row["repetition"],
        ) in copied
        records.append((row["task"], row["source_sha256"], row["source"], label))
    results = Counter()
    for task, key, source, label in records:
        if hashlib.sha256(source.encode()).hexdigest() != key:
            raise ValueError("Archived source checksum mismatch")
        detected = bool(find_overwrites(source, NAMES[task]))
        results[(task, detected, label)] += 1
    return results


if __name__ == "__main__":
    result = compare()
    print("task  sources  flagged+confirmed  flagged-only  missed  unflagged+clear")
    for task in (352, 108, 411):
        cells = [
            result[task, d, l]
            for d, l in ((True, True), (True, False), (False, True), (False, False))
        ]
        print(task, sum(cells), *cells)
