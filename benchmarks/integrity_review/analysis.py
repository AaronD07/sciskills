"""Report same-draft repairs and pair success on intact and compromised cases."""

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median
import random

from experiment import ARMS, FAMILIES, HERE, SEED, qualifying_sources, replay


def interval(groups):
    rng = random.Random(SEED)
    values = [(sum(v), len(v)) for _, v in sorted(groups.items())]
    ds = []
    for _ in range(10000):
        picked = rng.choices(values, k=len(values))
        ds.append(100 * sum(s for s, n in picked) / sum(n for s, n in picked))
    ds.sort()
    return [round(ds[i], 2) for i in (249, 9749)]


def summarize(rows):
    triples = defaultdict(dict)
    twins = defaultdict(dict)
    times = defaultdict(list)
    calls = Counter()
    statuses = Counter()
    for r in rows:
        key = (r["mode"], r["source"], r["model_key"])
        triples[(*key, r["variant"])][r["arm"]] = r
        twins[key].setdefault(r["arm"], []).append(r["grade"]["critical_pass"])
        times[r["arm"]].append(r["elapsed_seconds"])
        calls[r["arm"]] += len(r["calls"])
        statuses[r["status"]] += 1
    arms = ("draft", *ARMS)
    if not all(
        set(d) == set(arms) and all(len(v) == 2 for v in d.values())
        for d in twins.values()
    ):
        raise ValueError("Complete matched arms and twins required")
    by_arm = {}
    for a in arms:
        relevant = [t[a] for t in triples.values()]
        by_arm[a] = {
            "pairs_correct": sum(all(t[a]) for t in twins.values()),
            "critical_passes": sum(r["grade"]["critical_pass"] for r in relevant),
            "full_passes": sum(r["grade"]["full_pass"] for r in relevant),
            "median_seconds": round(median(times[a]), 2),
            "python_calls": calls[a],
        }
        if a != "draft":
            for label, initial, final in [
                ("repairs", False, True),
                ("regressions", True, False),
            ]:
                by_arm[a][label] = [
                    t[a]["id"]
                    for t in triples.values()
                    if t["draft"]["status"] == t[a]["status"] == "submitted"
                    and t["draft"]["grade"]["critical_pass"] == initial
                    and t[a]["grade"]["critical_pass"] == final
                ]
            by_arm[a]["intact_drafts_broken"] = [
                t[a]["id"]
                for t in triples.values()
                if t[a]["variant"] == "intact"
                and t[a]["id"] in by_arm[a]["regressions"]
            ]
            if a != "ordinary":
                by_arm[a]["repairs_beyond_ordinary"] = [
                    t[a]["id"]
                    for t in triples.values()
                    if t[a]["id"] in by_arm[a]["repairs"]
                    and t["ordinary"]["status"] == "submitted"
                    and not t["ordinary"]["grade"]["critical_pass"]
                ]
    contrasts = {}
    for a, b in [
        ("general", "ordinary"),
        ("specialist", "ordinary"),
        ("specialist", "general"),
    ]:
        groups = defaultdict(list)
        for (mode, source, model), t in twins.items():
            groups[(mode, source)].append(int(all(t[a])) - int(all(t[b])))
        delta = sum(map(sum, groups.values()))
        contrasts[a + "-" + b] = {
            "pair_gain_pp": round(100 * delta / len(twins), 2),
            "source_interval_pp": interval(groups),
        }
    return {
        "pairs": len(twins),
        "drafts": len(triples),
        "sources": len({(k[0], k[1]) for k in twins}),
        "arms": by_arm,
        "contrasts": contrasts,
        "statuses": dict(statuses),
    }


def report(root):
    results = {}
    allrows = []
    for mode in FAMILIES:
        dev = replay(root, mode, "dev")
        sources = qualifying_sources(dev)
        results[mode] = {
            "dev_sources_with_material_errors": sources,
            "dev_drafts": len(dev),
            "dev_error_drafts": sum(bool(r["grade"]["gate_errors"]) for r in dev),
        }
        if len(sources) >= 2:
            held = replay(root, mode, "holdout")
            results[mode]["holdout"] = summarize(held)
            allrows.extend(held)
    if allrows:
        results["all"] = summarize(allrows)
        for model in sorted({r["model_key"] for r in allrows}):
            results[model] = summarize([r for r in allrows if r["model_key"] == model])
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--results", type=Path, default=HERE / "results")
    print(json.dumps(report(ap.parse_args().results), indent=2))
