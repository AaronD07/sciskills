"""Summarize one frozen held-out cohort. Every paired case gets equal weight."""

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import json
from pathlib import Path
from statistics import mean

from verify import verify


def contrasts(rows):
    pairs = defaultdict(dict)
    for row in rows:
        key = tuple(row[k] for k in ("agent", "family", "split", "repetition"))
        if row["condition"] in pairs[key]:
            raise ValueError(f"Duplicate condition for {key}")
        pairs[key][row["condition"]] = row
    for key, arms in pairs.items():
        if set(arms) != {"baseline", "skill"}:
            raise ValueError(f"Missing condition for {key}")
    return {key: (arms["baseline"], arms["skill"]) for key, arms in pairs.items()}


def field_accuracy(row):
    checks = row["checks"].values()
    return Fraction(sum(checks), len(checks))


def summarize(pairs):
    """Average the per-answer fractions, even when families request different numbers of fields."""
    rows = list(pairs)
    accuracy = [(field_accuracy(a), field_accuracy(b)) for a, b in rows]
    deltas = [b - a for a, b in accuracy]
    completed = [d for d, pair in zip(deltas, rows) if all(r["status"] == "submitted" for r in pair)]
    statuses = Counter(r["status"] for pair in rows for r in pair)
    baseline_full = sum(a["full_pass"] for a, b in rows)
    skill_full = sum(b["full_pass"] for a, b in rows)
    difference = 100 * mean(deltas)
    return {
        "pairs": len(rows),
        "baseline_accuracy": round(float(mean(a for a, b in accuracy)), 6),
        "skill_accuracy": round(float(mean(b for a, b in accuracy)), 6),
        "difference_pp": round(float(difference), 3),
        "baseline_full": baseline_full,
        "skill_full": skill_full,
        "better": sum(x > 0 for x in deltas),
        "tied": sum(x == 0 for x in deltas),
        "worse": sum(x < 0 for x in deltas),
        "incomplete_pairs": len(rows) - len(completed),
        "submitted_pairs_difference_pp": round(float(100 * mean(completed)), 3) if completed else None,
        "statuses": dict(statuses),
        "meets_pilot_threshold": difference >= 10 and skill_full >= baseline_full,
    }


def report(directory):
    verify(directory)
    rows = [json.loads(line) for line in (directory / "trials.jsonl").read_text().splitlines()]
    pairs = contrasts(rows)
    groups = defaultdict(list)
    for (agent, family, split, _), pair in pairs.items():
        for label in ("all", agent, family, f"{agent}/{family}", f"{family}-{split}"):
            groups[label].append(pair)
    return {label: summarize(group) for label, group in groups.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    print(json.dumps(report(parser.parse_args().directory), indent=2))
