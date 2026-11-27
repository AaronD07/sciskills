"""Independently grade the published measurement oracles using only participant files."""

import csv
import hashlib
from io import StringIO
import json
from math import exp, log, isclose
from pathlib import Path
from statistics import correlation, mean
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from measurement import cases  # noqa: E402


def csvrows(files, filename):
    return list(csv.DictReader(StringIO(files[filename])))


def numbers_close(a, b):
    return (
        isclose(a, b, abs_tol=0.00011, rel_tol=0)
        if type(a) in (float, int) and type(b) in (float, int)
        else a == b
    )


def independently_score(name, f):
    out = {}
    if name == "uci-air":
        month = "06" if "June" in f["transmittal.txt"] else "04"
        for channel, prefix, threshold in (
            ("NMHC(GT)", "nmhc", 200),
            ("NO2(GT)", "no2", 90),
        ):
            r = [
                x
                for x in csvrows(f, "daily.csv")
                if x["channel"] == channel and x["date"].split("/")[1] == month
            ]
            n = sum(int(x["available"]) for x in r)
            slots = sum(int(x["sample_slots"]) for x in r)
            mu = sum(int(x["value_sum"]) for x in r) / n if n else None
            out.update(
                {
                    prefix + "_hours": n,
                    prefix + "_mean": mu,
                    prefix + "_action": "insufficient"
                    if n / slots < 0.6
                    else "elevated"
                    if mu > threshold
                    else "routine",
                }
            )
    elif name == "indometh":
        release = {}
        for event in sorted(
            csvrows(f, "accession.csv"), key=lambda x: int(x["recorded_at"])
        ):
            if int(event["release_on"]) <= 12:
                release[event["tube"]] = event["state"]
        for group, key in (("1", "area_a"), ("2", "area_b")):
            series = sorted(
                (float(x["hours"]), float(x["analyzer_value"]))
                for x in csvrows(f, "observations.csv")
                if x["subject"] == group
                and release.get(x["tube"], "released") == "released"
            )
            # Integrate the piecewise-linear concentration using the midpoint height on each interval.
            out[key] = (
                sum(
                    (hi - lo) * mean([a, b])
                    for (lo, a), (hi, b) in zip(series, series[1:])
                )
                if len(series) == 11
                else None
            )
        out["excess_pct"] = (
            100 * (out["area_b"] / out["area_a"] - 1) if all(out.values()) else None
        )
        out["conclusion"] = (
            "defer"
            if out["excess_pct"] is None
            else "above_margin"
            if out["excess_pct"] > 25
            else "within_margin"
        )
    elif name == "npk":
        releases = {}
        for r in sorted(csvrows(f, "history.csv"), key=lambda x: int(x["issue_day"])):
            if int(r["issue_day"]) <= 19:
                releases[r["balance"]] = r["state"]
        weights = {
            x["plot"]: float(x["scale_yield"]) for x in csvrows(f, "harvest.csv")
        }
        for arm, key in (("0", "control"), ("1", "treated")):
            members = [r for r in csvrows(f, "register.csv") if r["N"] == arm]
            pos = sum(
                releases[r["balance"]] == "released" and weights[r["plot"]] >= 55
                for r in members
            )
            unknown = sum(releases[r["balance"]] != "released" for r in members)
            lower, upper = pos / len(members), (pos + unknown) / len(members)
            out[key + "_rate"] = lower if unknown == 0 else None
            if arm == "1":
                out.update(
                    treated_lower=lower,
                    treated_upper=upper,
                    decision="meets"
                    if lower >= 0.5
                    else "misses"
                    if upper < 0.5
                    else "undetermined",
                )
    elif name == "mercury-pressure":
        p = {
            int(x["set_point_C"]): float(x["certified_mmHg"])
            for x in csvrows(f, "series.csv")
        }
        present = 160 in p
        out.update(
            reference=p.get(160),
            base=p[140],
            qualification="pending"
            if not present
            else "qualified"
            if p[160] >= 4
            else "below",
            planning=p[160] if present else exp(mean([log(p[140]), log(p[180])])),
            basis="reference" if present else "interpolation",
        )
    elif name == "black-cherry-inventory":
        rs = csvrows(f, "inventory.csv")
        measured = {r["tree"]: float(r["volume_ft3"]) for r in rs if r["volume_ft3"]}
        total = float(csvrows(f, "certified_balance.csv")[0]["value"])
        west = [x["tree"] for x in rs if x["lot"] == "west"]
        east = (
            total - sum(measured[t] for t in west)
            if all(t in measured for t in west)
            else None
        )
        out.update(
            census_total=total,
            parcel_total=sum(measured[str(t)] for t in range(1, 11)),
            east_total=east,
            east_basis="unresolved" if east is None else "mass_balance",
            settle="book" if east is not None else "hold",
        )
    elif name == "cabbage-assays":
        m = {r["head_tag"]: float(r["kg"]) for r in csvrows(f, "mass.csv")}
        y = {r["jar"]: float(r["VitC"]) for r in csvrows(f, "assay.csv")}
        links = {r["head_tag"]: r["jar"] for r in csvrows(f, "receipt.csv")}
        from itertools import permutations

        h = sorted(m.keys() - links.keys())
        candidates = [
            dict(links, **dict(zip(h, perm)))
            for perm in permutations(sorted(y.keys() - set(links.values())))
        ]
        possibilities = {
            round(
                correlation([m[k] for k in sorted(m)], [y[d[k]] for k in sorted(m)]), 8
            )
            for d in candidates
        }
        rho = possibilities.pop() if len(possibilities) == 1 else None
        out.update(
            head_mean=mean(m.values()),
            vitc_mean=mean(y.values()),
            correlation=rho,
            pairing="unresolved" if rho is None else "identified",
            claim="unresolved" if rho is None else "inverse" if rho < 0 else "other",
        )
    elif name == "stopping-distance":
        bins = csvrows(f, "bins.csv")
        counts = csvrows(f, "counter.csv")[0]
        if int(counts["boundary_ft"]) == 90:
            low = high = int(counts["count"])
        else:
            # Bound the number of qualifying values from the minimum and maximum
            # possible sums conditional on placing k values above the threshold.
            low = high = 0
            for b in bins:
                a, z, n, total = [
                    int(b[k])
                    for k in ("lo_inclusive", "hi_inclusive", "count", "sum_ft")
                ]
                if a > 90:
                    low += n
                    high += n
                elif z > 90:
                    options = [
                        k
                        for k in range(n + 1)
                        if a * (n - k) + 91 * k <= total <= 90 * (n - k) + z * k
                    ]
                    low += min(options)
                    high += max(options)
        out.update(
            mean_high=sum(int(b["sum_ft"]) for b in bins)
            / sum(int(b["count"]) for b in bins),
            mean_at20=mean(
                int(r["distance_ft"])
                for r in csvrows(f, "readout.csv")
                if r["speed_mph"] == "20"
            ),
            above90=low if low == high else None,
            min_above90=low,
            max_above90=high,
            decision="trigger" if low >= 3 else "clear" if high < 3 else "unresolved",
        )
    elif name == "sandstone-flow":
        imgs = csvrows(f, "images.csv")
        peri = {
            k: mean(float(x["perimeter"]) for x in imgs if x["core"] == k)
            for k in {x["core"] for x in imgs}
        }
        selected = [k for k in peri if peri[k] < 2000]
        assay = {r["core"]: float(r["mD"]) for r in csvrows(f, "flow_archive.csv")}
        obs = [assay[c] for c in selected if c in assay]
        imputed = [assay.get(c, 1e6 / peri[c]) for c in selected]
        full = len(obs) == len(selected)
        out.update(
            cores=len(selected),
            observed_mean=mean(obs),
            coverage=len(obs) / len(selected),
            population_measured_mean=mean(obs) if full else None,
            planning_mean=mean(imputed),
            certify="release" if full else "hold",
        )
    elif name == "spray-trial":
        ledger = {
            r["certificate"]: float(r["value"]) * (1e-4 if r["unit"] == "cm2" else 1)
            for r in sorted(csvrows(f, "lab_ledger.csv"), key=lambda x: int(x["day"]))
            if int(r["day"]) <= 10 and r["test"] == "effective_open_area"
        }
        regs = {
            (r["spray"], r["frame"]): r["certificate"]
            for r in csvrows(f, "frame_register.csv")
        }
        for arm in ["C", "D"]:
            rr = [r for r in csvrows(f, "sheets.csv") if r["spray"] == arm]
            count = sum(int(r["observed_count"]) for r in rr)
            areas = [ledger.get(regs[(arm, r["frame"])]) for r in rr]
            out[arm.lower() + "_count"] = count
            out[arm.lower() + "_density"] = (
                None if None in areas else count / sum(areas)
            )
        ratio = (
            out["d_density"] / out["c_density"]
            if out["d_density"] is not None
            else None
        )
        out.update(
            ratio=ratio,
            action="pending"
            if ratio is None
            else "review_D"
            if ratio > 1.5
            else "routine",
        )
    return out


def validate():
    manifest = json.loads((HERE / "sources.json").read_text())
    for name, entry in manifest.items():
        filename = "air_days.csv" if name == "air" else f"{name}.csv"
        expected_digest = entry["derived_sha256"] if name == "air" else entry["sha256"]
        if hashlib.sha256((HERE / filename).read_bytes()).hexdigest() != expected_digest:
            raise ValueError("Source digest mismatch: " + name)
    for split in ("dev", "holdout"):
        tasks = cases(split)
        for twin in range(0, len(tasks), 2):
            if tasks[twin]["files"]["TASK.md"] != tasks[twin + 1]["files"]["TASK.md"]:
                raise ValueError("Different participant task wording across twins")
        for case in tasks:
            expected = independently_score(case["source"], case["files"])
            if expected.keys() != case["gold"].keys() or not all(
                numbers_close(case["gold"][k], v) for k, v in expected.items()
            ):
                raise ValueError((case["id"], case["gold"], expected))
    print(
        "Verified all 18 measurement packet oracles, source checksums and matched instructions."
    )


if __name__ == "__main__":
    validate()
