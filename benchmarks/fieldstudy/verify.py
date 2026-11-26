"""Regrade the saved scientific answers and check the frozen evidence offline."""
import argparse
from collections import Counter
import inspect
import json
from pathlib import Path

from runner import digest, frozen_inputs, grade, normalized, prompt


def verify(directory):
    protocol = json.loads((directory / "protocol.json").read_text())
    rows = [json.loads(line) for line in (directory / "trials.jsonl").read_text().splitlines()]
    fields = ("agent", "family", "split", "repetition", "condition")
    planned = Counter(tuple(job[k] for k in fields) for job in protocol["jobs"])
    observed = Counter(tuple(row[k] for k in fields) for row in rows)
    if observed != planned or any(v != 1 for v in planned.values()):
        raise ValueError(f"{directory}: duplicate, unplanned or missing trials")
    if frozen_inputs(protocol["jobs"]) != protocol["inputs"]:
        raise ValueError(f"{directory}: inputs differ from the frozen materials")
    if "scorer_sha256" in protocol and digest(inspect.getsource(grade)) != protocol["scorer_sha256"]:
        raise ValueError(f"{directory}: scorer differs from its frozen version")
    for row in rows:
        key = ".".join(row[k] for k in ("family", "split", "condition"))
        _, answers = prompt(row["family"], row["split"], row["condition"])
        if (row["model"] != protocol["models"][row["agent"]]
            or digest(row["reply"]) != row["reply_sha256"]
            or row["prompt_sha256"] != protocol["inputs"][key]["prompt_sha256"]
            or digest(normalized(answers)) != protocol["inputs"][key]["gold_sha256"]):
            raise ValueError(f"{directory}: record provenance changed")
        computed = grade(row["reply"], answers)
        if any(row[k] != v for k, v in computed.items()):
            raise ValueError(f"{directory}: recorded grade differs")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    for directory in parser.parse_args().directories:
        print(f"{directory}: matched every check in {verify(directory)} trials")
