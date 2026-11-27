"""Summarize complete matched reviews and resample whole source clusters."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import random
from statistics import median

from study import SEED, cases_for, check_counts, labeled, schedule


def cluster_interval(clusters):
    rng = random.Random(SEED)
    totals = [(sum(values), len(values)) for _, values in sorted(clusters.items())]
    draws = []
    for _ in range(10000):
        picks = rng.choices(totals, k=len(totals))
        draws.append(100 * sum(x for x, _ in picks) / sum(n for _, n in picks))
    draws.sort()
    return [round(draws[i], 2) for i in (249, 9749)]


def summarize(triples):
    result = Counter()
    clusters = defaultdict(list)
    times, calls = defaultdict(list), defaultdict(list)
    statuses = Counter()
    for case, draft, ordinary, skill in triples:
        a, b, c = (r["grade"]["full_pass"] for r in (draft, ordinary, skill))
        result.update(
            {
                "draft_pass": a,
                "ordinary_pass": b,
                "skill_pass": c,
                "only_skill_repairs": not a and c and not b,
                "only_ordinary_repairs": not a and b and not c,
                "both_repair": not a and b and c,
                "ordinary_breaks": a and not b,
                "skill_breaks": a and not c,
            }
        )
        clusters[case["source"]].append(int(c) - int(b))
        for row in (draft, ordinary, skill):
            arm = row["arm"]
            times[arm].append(row["elapsed_seconds"])
            calls[arm].append(len(row["calls"]))
            statuses[(arm, row["status"])] += 1
    return {
        **result,
        "drafts": len(triples),
        "sources": len(clusters),
        "gain_pp": round(
            100 * (result["skill_pass"] - result["ordinary_pass"]) / len(triples), 2
        ),
        "cluster_interval_pp": cluster_interval(clusters),
        "median_seconds": {arm: round(median(t), 2) for arm, t in times.items()},
        "tool_calls": {arm: sum(c) for arm, c in calls.items()},
        "statuses": {
            f"{arm}/{status}": n for (arm, status), n in sorted(statuses.items())
        },
    }


def report(directory):
    cases = cases_for("holdout")
    check_counts("holdout", cases)
    rows = [
        json.loads(line)
        for line in (directory / "sessions.jsonl").read_text().splitlines()
    ]
    by_id = {r["id"]: r for r in rows}
    jobs = schedule("holdout", cases)
    if len(rows) != len(by_id) or set(by_id) != {
        labeled(j, arm) for j in jobs for arm in ("draft", "ordinary", "skill")
    }:
        raise ValueError("A complete matched schedule is required")
    groups = defaultdict(list)
    for j in jobs:
        case = cases[j["case"]]
        domain = "finance" if case["id"].startswith("fin") else "science"
        triple = (
            case,
            *(by_id[labeled(j, arm)] for arm in ("draft", "ordinary", "skill")),
        )
        for group in (domain, domain + "/" + j["model"], domain + "/" + case["route"]):
            groups[group].append(triple)
    result = {group: summarize(triples) for group, triples in sorted(groups.items())}
    primary = result["science"]
    primary["complete_submissions"] = all(
        s.endswith("/submitted") for s in primary["statuses"]
    )
    primary["meets_criterion"] = (
        primary["complete_submissions"]
        and primary["gain_pp"] >= 10
        and primary["cluster_interval_pp"][0] > 0
    )
    complete = [
        t for t in groups["science"] if all(r["status"] == "submitted" for r in t[1:])
    ]
    if complete and len(complete) < len(groups["science"]):
        result["science/completed_only"] = summarize(complete)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", type=Path)
    print(json.dumps(report(ap.parse_args().directory), indent=2))
