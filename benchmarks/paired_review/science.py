"""Real-data scientific review packets. Only files in a packet's files map go to the agent."""

import calendar
import csv
from collections import Counter, defaultdict
from datetime import date, timedelta
import io
import math
from pathlib import Path
import random
from statistics import mean, median, variance

DATA = Path(__file__).with_name("science_data")
CONTEXT = {
    "ChickWeight": "A longitudinal feeding experiment recorded each chick's weight in grams at scheduled ages in days. Diet codes are treatment labels.",
    "airquality": "Daily New York observations from May through September 1973. Ozone is in parts per billion, Solar.R is solar radiation, Wind is in mph, and Temp is in degrees Fahrenheit. Empty measurements are unavailable.",
    "CO2": "Monthly atmospheric carbon dioxide measurements from Mauna Loa, in ppm. Convert decimal time to the nearest month using round(time * 12), where integer years denote January.",
    "PlantGrowth": "Dry weights were measured for individual plants in a control group and two treatment groups.",
    "Theoph": "Theophylline concentration (mg/L) was measured in subjects at actual sampling times (hours) after an oral dose. Wt is weight in kg and Dose is dose in mg/kg.",
    "Loblolly": "Loblolly pine heights in feet were measured at several ages in years. Seed identifies the individual tree series.",
    "ToothGrowth": "Guinea pigs received orange juice (OJ) or ascorbic acid (VC) at one vitamin C dose (mg/day). Each observation is from a different animal.",
    "warpbreaks": "Warp breaks were counted on looms for two kinds of wool (A and B) at low, medium and high warp tension (L, M and H). Each row is one loom observation.",
    "esoph": "The grouped case-control study records oesophageal cancer cases and controls by age, alcohol and tobacco categories. Each CSV row is one cell, with frequency counts.",
    "OrchardSprays": "An 8 by 8 Latin square compares eight orchard spray treatments. decrease measures loss of solution weight. rowpos and colpos identify each physical cell.",
    "morley": "Michelson's light-speed experiment has five series of twenty ordered runs. The Speed column is observed km/s minus 299000.",
    "attenu": "California earthquake attenuation data record event, station, magnitude, distance (km) and peak horizontal acceleration (g). Station can be missing.",
}


def group(rows, *keys):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[key] for key in keys)].append(row)
    return groups


def numbers(rows, key):
    return [float(row[key]) for row in rows if row[key] != ""]


def month_index(row):
    return round(float(row["time"]) * 12)


def series(rows):
    return {month_index(r): float(r["value"]) for r in rows}


def dev_tasks(name, rows):
    if name == "ChickWeight":
        birds = group([r for r in rows if r["Diet"] == "1"], "Chick")
        spans = {}
        for (bird,), obs in birds.items():
            ordered = sorted(obs, key=lambda r: int(r["Time"]))
            a, b = ordered[0], ordered[-1]
            spans[bird] = (
                float(b["weight"]) - float(a["weight"]),
                int(b["Time"]) - int(a["Time"]),
            )
        gain = sum(v[0] for v in spans.values())
        days = sum(v[1] for v in spans.values())
        loo = [(gain - g) / (days - d) for g, d in spans.values()]
        yield (
            "numbers",
            "growth",
            "Estimate growth during observed follow-up for Diet 1. Report birds, pooled, equally_weighted and jackknife_se.",
            "Start at each bird's hatch weight and end at its last recorded weight. pooled is total grams gained per bird-day, equally_weighted is the mean individual rate, and jackknife_se uses a delete-one-bird jackknife of pooled.",
            {
                "birds": len(birds),
                "pooled": gain / days,
                "equally_weighted": mean(g / d for g, d in spans.values()),
                "jackknife_se": math.sqrt(
                    (len(loo) - 1) / len(loo) * sum((v - mean(loo)) ** 2 for v in loo)
                ),
            },
        )

        def day20(data):
            gains = defaultdict(list)
            for (diet, _), obs in group(data, "Diet", "Chick").items():
                w = {int(r["Time"]): float(r["weight"]) for r in obs}
                if 0 in w and 20 in w:
                    gains[diet].append(w[20] - w[0])
            return {diet: median(v) for diet, v in gains.items()}

        yield (
            "program",
            "hatch",
            "Produce a reusable implementation of the diet-level endpoint.",
            "For each diet, return the median individual weight gain between recorded days 0 and 20. Include a bird only with both dates. Return an object keyed by diet string. Omit diets without pairs. Each chick has at most one observation per day.",
            day20,
            "weight",
        )
        ids = sorted(
            (bird for bird, (gain, days) in spans.items() if days < 21), key=int
        )
        yield (
            "protocol",
            "retention",
            "Which Diet 1 chicks require the follow-up exception? Return ids and reviewed (total individual Diet 1 chicks).",
            "Review every animal assigned Diet 1. Flag any animal whose final measured age falls before scheduled day 21. Order IDs numerically and return them as strings.",
            {"ids": ids, "reviewed": len(birds)},
        )

    elif name == "airquality":
        pairs = [r for r in rows if r["Ozone"] and r["Solar.R"]]
        x = numbers(pairs, "Solar.R")
        y = numbers(pairs, "Ozone")
        slope = sum((a - mean(x)) * (b - mean(y)) for a, b in zip(x, y)) / sum(
            (a - mean(x)) ** 2 for a in x
        )
        yield (
            "numbers",
            "ozone",
            "Estimate the linear relationship of ozone to solar radiation. Return pairs, slope and intercept.",
            "Fit ordinary least squares with an intercept. Use every day with both model variables observed; other fields do not determine inclusion. Ozone is the outcome.",
            {"pairs": len(y), "slope": slope, "intercept": mean(y) - slope * mean(x)},
        )

        def longest(data):
            dates = sorted(
                date(1973, int(r["Month"]), int(r["Day"]))
                for r in data
                if r["Ozone"] and float(r["Ozone"]) > 60
            )
            length = best = 0
            prev = None
            for d in dates:
                length = length + 1 if prev and d == prev + timedelta(days=1) else 1
                best = max(best, length)
                prev = d
            return best

        yield (
            "program",
            "episodes",
            "Implement the ozone-episode duration metric.",
            "Return the maximum length in consecutive calendar days for which Ozone exceeds 60. Missing or absent days interrupt an episode. The input has at most one record per date. Return 0 when no day qualifies.",
            longest,
            "Ozone",
        )
        frac = {
            m: sum(bool(r["Ozone"] and r["Solar.R"]) for r in obs)
            / calendar.monthrange(1973, int(m))[1]
            for (m,), obs in group(rows, "Month").items()
        }
        yield (
            "protocol",
            "coverage",
            "Identify months qualifying for complete-pair reporting. Return months and retained_days.",
            "A month qualifies when at least 70% of its calendar days have both Ozone and Solar.R observed. Retained days are complete-pair days in qualifying months. Month IDs are decimal strings in calendar order.",
            {
                "months": sorted([m for m, f in frac.items() if f >= 0.7], key=int),
                "retained_days": sum(frac[r["Month"]] >= 0.7 for r in pairs),
            },
        )

    elif name == "CO2":
        obs = series(rows)
        diffs = [v - obs[t - 12] for t, v in obs.items() if t - 12 in obs]
        yield (
            "numbers",
            "annual",
            "Summarize year-over-year increases. Return pairs, mean_gain and median_gain in ppm.",
            "Compute one difference for each month whose observation from exactly 12 calendar months earlier is available. Use all such differences.",
            {
                "pairs": len(diffs),
                "mean_gain": mean(diffs),
                "median_gain": median(diffs),
            },
        )

        def amplitude(data):
            annual = defaultdict(list)
            for t, v in series(data).items():
                annual[t // 12].append(v)
            return {str(y): max(v) - min(v) for y, v in annual.items() if len(v) == 12}

        yield (
            "program",
            "seasons",
            "Write an annual seasonal amplitude routine.",
            "A complete January through December calendar year contributes max minus min concentration. Return those amplitudes by year as a JSON object with string keys. There is at most one record per month.",
            amplitude,
            "value",
        )
        eligible = [
            str(y)
            for y in sorted({t // 12 for t in obs})
            if all(obs.get(y * 12 + i, 0) > 350 for i in range(12))
        ]
        yield (
            "protocol",
            "release",
            "Identify years meeting the sustained 350 ppm criterion. Return years and first_year.",
            "Every month January through December must have an observed concentration strictly greater than 350. Use strings for ascending year IDs and for the earliest eligible year.",
            {"years": eligible, "first_year": eligible[0]},
        )

    elif name == "PlantGrowth":
        samples = {
            g: numbers(rr, "weight") for (g,), rr in group(rows, "group").items()
        }
        a, b = samples["trt1"], samples["trt2"]
        v1, v2 = variance(a) / len(a), variance(b) / len(b)
        yield (
            "numbers",
            "contrast",
            "Estimate the treatment difference with Welch uncertainty. Return difference, se and df.",
            "Compare trt2 minus trt1 using arithmetic group means. Report the unpooled standard error and Welch-Satterthwaite degrees of freedom based on unbiased sample variances.",
            {
                "difference": mean(b) - mean(a),
                "se": math.sqrt(v1 + v2),
                "df": (v1 + v2) ** 2 / (v1**2 / (len(a) - 1) + v2**2 / (len(b) - 1)),
            },
        )

        def robust(data):
            result = {}
            for (g,), rr in group(data, "group").items():
                vals = numbers(rr, "weight")
                if vals:
                    center = median(vals)
                    result[g] = median(abs(x - center) for x in vals)
            return result

        yield (
            "program",
            "spread",
            "Implement a robust within-treatment spread measure.",
            "Return the raw median absolute deviation from the group median for each group as a JSON object. A singleton has spread zero. Exclude missing weights and omit empty groups.",
            robust,
            "weight",
        )
        above = [
            r
            for r in rows
            if r["group"] != "ctrl" and float(r["weight"]) > max(samples["ctrl"])
        ]
        yield (
            "protocol",
            "extremes",
            "Identify treated specimens exceeding the control reference. Return ids and control_max.",
            "The reference is the maximum observed control dry weight across all controls. Only strictly higher non-control observations qualify. Use rownames as string specimen IDs, sorted numerically.",
            {
                "ids": sorted([r["rownames"] for r in above], key=int),
                "control_max": max(samples["ctrl"]),
            },
        )


def program_tests(rows, reference, field):
    """A held-back subset and changed measurements check transfer; reversal checks order."""
    subset = [dict(r) for i, r in enumerate(rows) if i % 5 != 1]
    changed = [dict(r) for r in rows]
    for i, r in enumerate(changed):
        if i % 3 == 0 and r[field]:
            r[field] = str(int(float(r[field])) + 19)
    shuffled = list(rows)
    random.Random(613).shuffle(shuffled)
    return [
        {"rows": v, "expected": reference(v)}
        for v in (rows, subset, changed, shuffled, [])
    ]


def cases(split):
    if split == "dev":
        sources = ("ChickWeight", "airquality", "CO2", "PlantGrowth")
        build = dev_tasks
    elif split == "science":
        sources = (
            "Theoph",
            "Loblolly",
            "ToothGrowth",
            "warpbreaks",
            "esoph",
            "OrchardSprays",
            "morley",
            "attenu",
        )
        build = heldout_tasks
    else:
        raise ValueError(split)
    result = []
    for name in sources:
        data = (DATA / (name + ".csv")).read_text()
        rows = list(csv.DictReader(io.StringIO(data)))
        for route, tag, request, method, expected, *rest in build(name, rows):
            task = request + " Read methods.md and observations.csv."
            if route == "program":
                task += " Write solution.py exposing solve(rows), where rows is a list of dictionaries with string values and CSV header keys. It must return the JSON-compatible value defined in methods.md. Use the Python standard library. Input order is unspecified."
            else:
                task += " Write the requested fields as a single JSON object in answer.json. Give numbers to at least six decimal places where needed."
            files = {
                "TASK.md": task + "\n",
                "methods.md": CONTEXT[name] + "\n\n" + method + "\n",
                "observations.csv": data,
            }
            case = {
                "id": name.lower() + "-" + tag,
                "source": name,
                "route": route,
                "files": files,
                "gold": {},
            }
            if route == "program":
                case["tests"] = program_tests(rows, expected, rest[0])
            else:
                case["gold"] = expected
                if rest:
                    files.update(rest[0])
            result.append(case)
    return result


def table(header, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def positive_auc(points, until):
    """Integrate the positive part of a piecewise linear curve through until."""
    area = 0
    for (a, u), (b, v) in zip(points, points[1:]):
        if a >= until:
            break
        right = min(b, until)
        w = u + (v - u) * (right - a) / (b - a)
        width = right - a
        if min(u, w) >= 0:
            area += width * (u + w) / 2
        elif max(u, w) > 0:
            area += width * max(u, w) ** 2 / (2 * abs(w - u))
    return area


def heldout_tasks(name, rows):
    if name == "Theoph":
        curves = {
            s: sorted((float(r["Time"]), float(r["conc"])) for r in rr)
            for (s,), rr in group(rows, "Subject").items()
        }
        treatments = {r["Subject"]: float(r["Dose"]) for r in rows}
        exposure = {}
        for s, points in curves.items():
            base = points[0][1]
            area = positive_auc([(t, c - base) for t, c in points], 8)
            exposure[s] = area / treatments[s]
        yield (
            "numbers",
            "exposure",
            "Report subjects, median_exposure, peak_subject, and decision for the registered early exposure endpoint.",
            "Use observed samples and linear interpolation. Integrate from hour zero to hour eight inclusive after subtracting that subject's first concentration. Values below zero contribute zero throughout the interpolated curve. Divide each integral by the subject's mg/kg dose. Report the median across subjects and the subject ID (string) with greatest normalized exposure. The follow-up decision is 'advance' if the median reaches 10 and 'defer' otherwise.",
            {
                "subjects": len(exposure),
                "median_exposure": median(exposure.values()),
                "peak_subject": max(exposure, key=exposure.get),
                "decision": "advance" if median(exposure.values()) >= 10 else "defer",
            },
        )

        def half_time(data):
            result = {}
            for (s,), rr in group(data, "Subject").items():
                seq = sorted((float(r["Time"]), float(r["conc"])) for r in rr)
                peak = max(v for t, v in seq)
                p = next(i for i, (_, v) in enumerate(seq) if v == peak)
                for (a, u), (b, v) in zip(seq[p:], seq[p + 1 :]):
                    if u > peak / 2 >= v:
                        result[s] = a + (b - a) * (u - peak / 2) / (u - v)
                        break
            return result

        yield (
            "program",
            "halftime",
            "Implement observed post-peak half-concentration crossing times.",
            "Use the earliest sample attaining the subject's maximum. Moving forward in actual sampling time, find the first segment from strictly above to at or below half of that maximum. Return the interpolated absolute time in hours by subject ID string. Omit subjects without a qualifying segment. Times are distinct within subject.",
            half_time,
            "conc",
        )
        docket = [
            ("5", 1, 1, "hold", "yes"),
            ("5", 2, 4, "release", "yes"),
            ("16", 1, 3, "hold", "yes"),
            ("49", 1, 3, "hold", "yes"),
            ("49", 2, 6, "release", "yes"),
            ("49", 3, 4, "release", "no"),
            ("104", 1, 5, "hold", "yes"),
            ("105", 1, 4, "hold", "yes"),
            ("6", 1, 5, "hold", "no"),
        ]
        states = {}
        for rid, rev, day, state, signed in docket:
            if day <= 5 and signed == "yes" and rev > states.get(rid, (0, ""))[0]:
                states[rid] = rev, state
        eligible = [
            r for r in rows if states.get(r["rownames"], (0, "release"))[1] == "release"
        ]
        audit = {
            s: max(numbers(rr, "conc"))
            for (s,), rr in group(eligible, "Subject").items()
            if any(float(r["Time"]) == 0 and float(r["conc"]) <= 0.5 for r in rr)
        }
        high = sorted((s for s, c in audit.items() if c >= 9), key=int)
        yield (
            "protocol",
            "assay-release",
            "Prepare the frozen high-exposure panel. Return eligible_subjects (count), high_ids, and max_retained_concentration among eligible subjects.",
            "For this reanalysis, QC.csv is a constructed docket keyed by the exact assay rownames. The report freezes at day 5 inclusive. Use the highest signed revision available by then for each assay; an assay with no effective entry is released. A hold removes that assay. Keep a subject only if a released pre-dose time-zero sample has concentration at most 0.5. Flag a retained subject whose maximum released concentration reaches 9. Return numerically ordered string IDs.",
            {
                "eligible_subjects": len(audit),
                "high_ids": high,
                "max_retained_concentration": max(audit.values()),
            },
            {
                "QC.csv": table(
                    ("assay", "revision", "filed_day", "state", "signed"), docket
                )
            },
        )

    elif name == "Loblolly":
        trees = {
            s: {int(r["age"]): float(r["height"]) for r in rr}
            for (s,), rr in group(rows, "Seed").items()
        }
        early = [(g[15] - g[5]) / 10 for g in trees.values()]
        late = [(g[25] - g[15]) / 10 for g in trees.values()]
        decline = [100 * (first - last) / first for first, last in zip(early, late)]
        yield (
            "numbers",
            "deceleration",
            "Report median_individual_pct, aggregate_pct, and covariance for the growth slowdown.",
            "Each seed contributes a 5–15 year rate and a 15–25 year rate, in feet/year. Express decline as 100*(early-late)/early. First take the median of tree-specific declines. Separately compute decline from the two mean rates. Give the sample covariance of the paired early and late rates (denominator n-1).",
            {
                "median_individual_pct": median(decline),
                "aggregate_pct": 100 * (mean(early) - mean(late)) / mean(early),
                "covariance": sum(
                    (a - mean(early)) * (b - mean(late)) for a, b in zip(early, late)
                )
                / (len(early) - 1),
            },
        )

        def interpolation(data):
            result = {}
            for (s,), rr in group(data, "Seed").items():
                seq = sorted((float(r["age"]), float(r["height"])) for r in rr)
                errors = [
                    abs(h - (v + (w - v) * (t - a) / (b - a)))
                    for (a, v), (t, h), (b, w) in zip(seq, seq[1:], seq[2:])
                ]
                if errors:
                    result[s] = max(errors)
            return result

        yield (
            "program",
            "interpolation",
            "Implement the tree-level interpolation diagnostic.",
            "Omit each internal age in turn and use straight-line interpolation between its two nearest surrounding available ages on the same tree. Return the largest absolute prediction error per tree as an object keyed by Seed. Omit trees with fewer than three ages. No tree-age key is duplicated.",
            interpolation,
            "height",
        )
        lots = [
            ("N1", "301", "307"),
            ("N2", "303", "329"),
            ("N3", "305", "311"),
            ("N4", "309", "315"),
            ("N5", "319", "323"),
            ("N6", "325", "331"),
        ]
        decisions = [
            ("N2", 1, 12, "review"),
            ("N2", 2, 15, "allow"),
            ("N3", 1, 10, "review"),
            ("N3", 2, 16, "allow"),
            ("N6", 1, 14, "review"),
        ]
        status = {}
        for lot, v, day, state in decisions:
            if day <= 15:
                status[lot] = state
        gaps = {
            k: (trees[a][25] - trees[a][10]) - (trees[b][25] - trees[b][10])
            for k, a, b in lots
            if status.get(k, "allow") == "allow"
        }
        yield (
            "protocol",
            "matched-lots",
            "Compute the registered paired-lot endpoint at the release freeze. Return lot_ids, mean_gap and positive_lots.",
            "The constructed lot registry defines lead and matched reference trees. In ledger.csv use the highest revision available by day 15 inclusive per lot; the lot defaults to allow. Only allowed, complete pairs with ages 10 and 25 in both trees contribute. Compute lead's 10-to-25 gain minus reference's gain in feet, equally weighted across lots. Return contributing lot strings alphabetically and count strict positives.",
            {
                "lot_ids": sorted(gaps),
                "mean_gap": mean(gaps.values()),
                "positive_lots": sum(x > 0 for x in gaps.values()),
            },
            {
                "lots.csv": table(("lot", "lead_seed", "reference_seed"), lots),
                "ledger.csv": table(
                    ("lot", "revision", "available_day", "status"), decisions
                ),
            },
        )

    elif name == "ToothGrowth":
        samples = {
            (dose, supp): numbers(g, "len")
            for (dose, supp), g in group(rows, "dose", "supp").items()
        }
        targets = {"0.5": 2, "1": 5, "2": 3}
        effect = se2 = 0
        for dose, count in targets.items():
            w = count / sum(targets.values())
            a, b = samples[dose, "OJ"], samples[dose, "VC"]
            effect += w * (mean(a) - mean(b))
            se2 += w * w * (variance(a) / len(a) + variance(b) / len(b))
        yield (
            "numbers",
            "dose-target",
            "Estimate the target-population supplement contrast. Return target_difference, se and upper95.",
            "The constructed target.csv gives relative dose frequencies in the target population. Standardize OJ minus VC mean tooth length to that mix. Samples are independent across animals and cells. Use unbiased within-cell variances and fixed target weights. Give the upper endpoint of a normal 95% interval using multiplier 1.96.",
            {
                "target_difference": effect,
                "se": math.sqrt(se2),
                "upper95": effect + 1.96 * math.sqrt(se2),
            },
            {"target.csv": table(("dose", "relative_frequency"), targets.items())},
        )

        def shift(data):
            result = {}
            for (d,), rr in group(data, "dose").items():
                a = numbers([r for r in rr if r["supp"] == "OJ"], "len")
                b = numbers([r for r in rr if r["supp"] == "VC"], "len")
                if a and b:
                    result[d] = median(x - y for x in a for y in b)
            return result

        yield (
            "program",
            "shift",
            "Implement the stratified two-sample location-shift estimator.",
            "Within each dose form every cross-supplement pair and take the median of OJ minus VC lengths. Each distinct animal counts even when lengths tie. Return an object keyed by the original dose strings, omitting doses missing either supplement.",
            shift,
            "len",
        )
        registry = [
            ("A", "0.5", 10.0, 0.30),
            ("B", "1", 20.0, 0.40),
            ("C", "2", 25.0, 0.30),
        ]
        changes = [
            ("B", 18.0, 4, 1),
            ("C", 26.0, 4, 1),
            ("C", 27.0, 7, 2),
            ("A", 12.0, 3, 1),
            ("A", 11.0, 5, 2),
        ]
        limits = {code: cut for code, d, cut, w in registry}
        for code, cut, day, rev in sorted(changes, key=lambda c: c[3]):
            if day <= 5:
                limits[code] = cut
        rr = {}
        risky = []
        for code, d, cut, w in registry:
            rates = {
                s: mean(x >= limits[code] for x in samples[d, s]) for s in ("OJ", "VC")
            }
            rr[code] = rates
            if rates["OJ"] < rates["VC"]:
                risky.append(code)
        yield (
            "protocol",
            "response-fractions",
            "Audit the binary response table under the registered release. Return lower_oj_bins, target_oj and target_vc as fractions.",
            "For this constructed release, join the bins in registry.csv to dose. Apply the highest threshold revision published by day 5 inclusive, separately per bin, with the registry threshold as fallback. An animal responds at or above its bin's threshold. For each supplement calculate the target-weighted mean of within-bin response fractions. List alphabetical bin codes with a strictly lower OJ fraction than VC.",
            {
                "lower_oj_bins": sorted(risky),
                "target_oj": sum(w * rr[c]["OJ"] for c, _, _, w in registry),
                "target_vc": sum(w * rr[c]["VC"] for c, _, _, w in registry),
            },
            {
                "registry.csv": table(
                    ("bin", "dose", "threshold", "target_weight"), registry
                ),
                "revisions.csv": table(
                    ("bin", "threshold", "published_day", "revision"), changes
                ),
            },
        )

    elif name == "warpbreaks":
        samples = {
            (w, t): numbers(obs, "breaks")
            for (w, t), obs in group(rows, "wool", "tension").items()
        }
        weights = {"L": 2, "M": 3, "H": 5}
        probs = {}
        for t in weights:
            a, b = samples["A", t], samples["B", t]
            probs[t] = mean((x > y) + 0.5 * (x == y) for x in a for y in b)
        pooled_a = numbers([r for r in rows if r["wool"] == "A"], "breaks")
        pooled_b = numbers([r for r in rows if r["wool"] == "B"], "breaks")
        yield (
            "numbers",
            "loom-risk",
            "Estimate probability of superiority for loom break counts. Return stratified, unstratified and ties_l.",
            "Compare independent draws of an A and a B loom, scoring A>B as 1 and ties as 0.5. For stratified, draw two looms at a common tension drawn from the target mix in allocation.csv. For unstratified, draw from each wool's complete observed sample independently. ties_l is the integer number of tied ordered A,B observation pairs at L.",
            {
                "stratified": sum(weights[t] * v for t, v in probs.items())
                / sum(weights.values()),
                "unstratified": mean(
                    (x > y) + 0.5 * (x == y) for x in pooled_a for y in pooled_b
                ),
                "ties_l": sum(
                    x == y for x in samples["A", "L"] for y in samples["B", "L"]
                ),
            },
            {"allocation.csv": table(("tension", "target_units"), weights.items())},
        )

        def tail(data):
            result = {}
            for (w, t), rr in group(data, "wool", "tension").items():
                vals = sorted(numbers(rr, "breaks"), reverse=True)
                mass = len(vals) / 4
                whole = int(mass)
                total = sum(vals[:whole])
                if mass > whole:
                    total += (mass - whole) * vals[whole]
                result[w + "/" + t] = total / mass
            return result

        yield (
            "program",
            "loom-tail",
            "Implement expected shortfall of breaks in each wool and tension cell.",
            "For each observed cell return the mean break count in the worst one-quarter of its empirical mass. Consume highest observations first, using a fractional boundary observation to fill exactly n/4. Keys are wool/tension, e.g. A/L.",
            tail,
            "breaks",
        )
        allocation = [
            ("east", "L", 10, 3),
            ("east", "M", 5, 9),
            ("east", "H", 2, 4),
            ("west", "L", 8, 2),
            ("west", "M", 5, 9),
            ("west", "H", 4, 4),
        ]
        shifts = [
            ("east", "L", 4, 1),
            ("east", "M", -2, 1),
            ("west", "H", 4, 0),
            ("west", "L", -1, 1),
        ]
        base = sum(
            a * mean(samples["A", t]) + b * mean(samples["B", t])
            for _, t, a, b in allocation
        )
        delta = {
            site: sum(
                n * (mean(samples["B", t]) - mean(samples["A", t]))
                for st, t, n, approved in shifts
                if st == site and approved
            )
            for site in ("east", "west")
        }
        yield (
            "protocol",
            "fleet-change",
            "Project the approved loom reallocation. Return expected_before, expected_after, and sites_with_reduction.",
            "Use measured arithmetic means for each wool/tension cell to project total expected breaks across both facilities in fleet.csv. In transfers.csv a positive transfer moves that number of looms from A to B at unchanged tension; negative reverses the transfer. Implement only approved rows. List sites with strictly lower expected total in alphabetical order.",
            {
                "expected_before": base,
                "expected_after": base + sum(delta.values()),
                "sites_with_reduction": sorted(s for s, d in delta.items() if d < 0),
            },
            {
                "fleet.csv": table(
                    ("site", "tension", "looms_A", "looms_B"), allocation
                ),
                "transfers.csv": table(
                    ("site", "tension", "transfer", "approved"), shifts
                ),
            },
        )
    else:
        yield from additional_tasks(name, rows)


def additional_tasks(name, rows):
    if name == "esoph":
        num = den = 0
        crude = [0] * 4
        informative = 0
        for _, rr in group(rows, "agegp", "tobgp").items():
            high = [r for r in rr if r["alcgp"] in ("80-119", "120+")]
            low = [r for r in rr if r["alcgp"] == "0-39g/day"]
            a, b, c, d = (
                sum(int(r[k]) for r in rs)
                for rs, k in [
                    (high, "ncases"),
                    (high, "ncontrols"),
                    (low, "ncases"),
                    (low, "ncontrols"),
                ]
            )
            crude = [u + v for u, v in zip(crude, (a, b, c, d))]
            if a + b + c + d:
                num += a * d / (a + b + c + d)
                den += b * c / (a + b + c + d)
                informative += int(a * d + b * c > 0)
        a, b, c, d = crude
        yield (
            "numbers",
            "adjusted-odds",
            "Report adjusted_or, crude_or and informative_strata for the extreme alcohol exposure contrast.",
            "Compare at least 80 g/day (combine the upper two bands) to 0–39 g/day. Exclude 40–79. Stratify by age crossed with tobacco, filling absent cells with zero people. Compute the Mantel-Haenszel common odds ratio from counts, without continuity corrections. For the crude ratio, pool all retained people. A stratum is informative when either cross-product in its 2x2 table is positive.",
            {
                "adjusted_or": num / den,
                "crude_or": a * d / (b * c),
                "informative_strata": informative,
            },
        )

        def midpoint(data):
            probs = {}
            order = ["0-9g/day", "10-19", "20-29", "30+"]
            for (age,), rr in group(data, "agegp").items():
                ca = Counter()
                co = Counter()
                for r in rr:
                    ca[r["tobgp"]] += int(r["ncases"])
                    co[r["tobgp"]] += int(r["ncontrols"])
                n = sum(ca.values()) * sum(co.values())
                if n:
                    probs[age] = (
                        sum(
                            ca[x] * co[y] * ((i > j) + 0.5 * (i == j))
                            for i, x in enumerate(order)
                            for j, y in enumerate(order)
                        )
                        / n
                    )
            return probs

        yield (
            "program",
            "ordinal",
            "Implement an ordinal tobacco-exposure discrimination index by age.",
            "Within each age group, draw one case and one control independently according to their frequency counts, pooling alcohol bands. Score 1 when the case has higher tobacco exposure and 0.5 for ties. Return the expected score for each age string with at least one case and control. The tobacco groups in ascending order are 0-9g/day, 10-19, 20-29, 30+.",
            midpoint,
            "ncases",
        )
        labels = {
            "25-34": "junior",
            "35-44": "junior",
            "45-54": "middle",
            "55-64": "middle",
            "65-74": "senior",
            "75+": "senior",
        }
        bundle = defaultdict(lambda: [0, 0])
        for r in rows:
            k = labels[r["agegp"]] + "/" + r["alcgp"]
            bundle[k][0] += int(r["ncases"])
            bundle[k][1] += int(r["ncontrols"])
        suppressed = {k for k, (a, b) in bundle.items() if min(a, b) < 12}
        public = set(bundle) - suppressed
        second = set()
        for label in sorted(set(labels.values())):
            cells = [k for k in bundle if k.split("/")[0] == label]
            if sum(k in suppressed for k in cells) == 1:
                pick = min(
                    [k for k in cells if k in public], key=lambda k: (sum(bundle[k]), k)
                )
                second.add(pick)
        hidden = suppressed | second
        yield (
            "protocol",
            "disclosure",
            "Apply the disclosure register to the proposed public table. Return primary_cells, final_hidden and published_people.",
            "Construct one released cell per reporting age label (age-map.csv) and original alcohol category. Sum cases and controls across component ages and tobacco strata. Initially hide every cell with fewer than 12 cases or fewer than 12 controls. In each age label with exactly one primary suppression, also hide the remaining cell with smallest combined headcount (ties by lexical cell key). Give count of primary suppressions, sorted final hidden strings in label/alcohol form, and total people in visible cells. Age labels and disclosure thresholds are constructed for this reanalysis.",
            {
                "primary_cells": len(suppressed),
                "final_hidden": sorted(hidden),
                "published_people": sum(
                    sum(v) for k, v in bundle.items() if k not in hidden
                ),
            },
            {"age-map.csv": table(("agegp", "reporting_label"), labels.items())},
        )

    elif name == "OrchardSprays":
        y = numbers(rows, "decrease")
        gm = mean(y)

        def term(col):
            return sum(
                len(rr) * (mean(numbers(rr, "decrease")) - gm) ** 2
                for rr in group(rows, col).values()
            )

        tss = sum((v - gm) ** 2 for v in y)
        tr = term("treatment")
        err = tss - tr - term("rowpos") - term("colpos")
        yield (
            "numbers",
            "latin-square",
            "Report residual_df, treatment_f and partial_eta2 for the spatially blocked experiment.",
            "Fit an additive Latin-square model with an intercept and fixed categorical row, column and treatment terms. Use the residual mean square from the full model as the denominator of the treatment F statistic. The partial eta squared is treatment sum of squares divided by treatment plus residual sums of squares.",
            {
                "residual_df": 42,
                "treatment_f": (tr / 7) / (err / 42),
                "partial_eta2": tr / (tr + err),
            },
        )

        def adjacent(data):
            pos = {
                (int(r["rowpos"]), int(r["colpos"])): float(r["decrease"]) for r in data
            }
            out = defaultdict(list)
            for r in data:
                x, y = int(r["rowpos"]), int(r["colpos"])
                near = [
                    pos[p]
                    for p in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]
                    if p in pos
                ]
                if near:
                    out[r["treatment"]].append(float(r["decrease"]) - mean(near))
            return {k: median(v) for k, v in out.items()}

        yield (
            "program",
            "neighbor",
            "Implement a spatial local-contrast diagnostic.",
            "For each measured cell subtract the arithmetic mean of its available orthogonal neighbors from its own decrease. Omit cells with no measured neighbors. Report the median of these cell contrasts within each represented treatment. The grid has no wraparound and each coordinate occurs at most once.",
            adjacent,
            "decrease",
        )
        spills = [
            ("P", "east", 2, 3, 1, 4, "open"),
            ("P", "east", 2, 3, 2, 6, "clear"),
            ("Q", "west", 1, 6, 1, 3, "open"),
            ("R", "west", 4, 1, 1, 5, "open"),
            ("R", "west", 4, 1, 2, 5, "clear"),
            ("S", "east", 3, 7, 1, 8, "open"),
        ]
        history = {}
        for ref, bank, lane, col, rev, day, flag in sorted(spills, key=lambda z: z[4]):
            if day <= 5:
                history[ref] = bank, lane, col, flag
        affected = set()
        for bank, lane, col, flag in history.values():
            if flag != "open":
                continue
            row = 4 + lane if bank == "east" else 5 - lane
            affected.update(
                [
                    (row, col),
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                ]
            )
        live = [r for r in rows if (int(r["rowpos"]), int(r["colpos"])) not in affected]
        by = {
            t: mean(numbers(g, "decrease"))
            for (t,), g in group(live, "treatment").items()
        }
        yield (
            "protocol",
            "spill-panel",
            "Construct the clean panel at day 5. Return excluded_count, excluded_cells and h_minus_a after exclusion.",
            "Use only incident records available through day 5. Highest revision per incident controls. Each still-open incident excludes its mapped cell and all in-grid orthogonal neighbors. Use the mapping in layout.csv; columns retain their displayed numeric positions. Count distinct excluded observed cells and list their rownames as numerically sorted strings. Compute difference between the remaining arithmetic mean for treatment H and that for A. Logs and bank labels were constructed for this audit.",
            {
                "excluded_count": len(rows) - len(live),
                "excluded_cells": sorted(
                    (r["rownames"] for r in rows if r not in live), key=int
                ),
                "h_minus_a": by["H"] - by["A"],
            },
            {
                "incidents.csv": table(
                    (
                        "incident",
                        "bank",
                        "lane",
                        "column",
                        "revision",
                        "available_day",
                        "status",
                    ),
                    spills,
                ),
                "layout.csv": table(
                    ("bank", "lane", "rowpos"),
                    [
                        (b, i, 4 + i if b == "east" else 5 - i)
                        for b in ("east", "west")
                        for i in range(1, 5)
                    ],
                ),
            },
        )

    elif name == "morley":
        by = {
            s: sorted(rr, key=lambda r: int(r["Run"]))
            for (s,), rr in group(rows, "Expt").items()
        }
        residuals = {
            s: [v - mean(numbers(rr, "Speed")) for v in numbers(rr, "Speed")]
            for s, rr in by.items()
        }
        ac_num = sum(
            sum(x * y for x, y in zip(seq, seq[1:])) for seq in residuals.values()
        )
        ac_den = sum(sum(x * x for x in seq[:-1]) for seq in residuals.values())
        estimates = [mean(numbers(rr, "Speed")) + 299000 for rr in by.values()]
        yield (
            "numbers",
            "repeatability",
            "Summarize series-to-series and within-series behavior. Return absolute_speed, series_se, and lag_slope.",
            "Use equal weights for the five series means and report their mean in km/s. Estimate the standard error using the series as independent units. For lag_slope subtract each series' mean from its readings, form all successive run pairs within that series and pool them. Fit current residual on previous residual with the intercept fixed at zero.",
            {
                "absolute_speed": mean(estimates),
                "series_se": math.sqrt(variance(estimates) / len(estimates)),
                "lag_slope": ac_num / ac_den,
            },
        )

        def first_alarm(data):
            out = {}
            for (key,), rr in group(data, "Expt").items():
                obs = {int(r["Run"]): float(r["Speed"]) for r in rr}
                if not all(i in obs for i in (1, 2, 3)):
                    continue
                base = median(obs[i] for i in [1, 2, 3])
                score = 0
                prior = 3
                for n in sorted(i for i in obs if i > 3):
                    if n != prior + 1:
                        score = 0
                    score = max(0, score + obs[n] - base - 10)
                    if score >= 75:
                        out[key] = n
                        break
                    prior = n
            return out

        yield (
            "program",
            "drift-alarm",
            "Return the first detected upward drift per experiment.",
            "Use the median Speed of runs 1,2,3 as a fixed baseline; omit series missing a baseline run. Starting at run 4 with cumulative score zero, update score=max(0,score+Speed-baseline-10). Reset to zero before processing the next available run after a gap. Alarm on the first score >=75. Return only series with an alarm, keyed by experiment string with numerical run number. Run IDs are unique per experiment.",
            first_alarm,
            "Speed",
        )
        assignments = [("1", "a"), ("2", "a"), ("3", "b"), ("4", "b"), ("5", "c")]
        cal = [
            ("a", 1, 1, 1, 8),
            ("a", 9, 1, 2, -5),
            ("a", 9, 2, 7, -15),
            ("b", 1, 1, 1, 4),
            ("b", 11, 1, 5, 13),
            ("c", 1, 1, 7, 15),
        ]
        instruments = dict(assignments)
        corr = defaultdict(list)
        for r in rows:
            opt = [
                (start, rev, adj)
                for device, start, rev, day, adj in cal
                if device == instruments[r["Expt"]]
                and start <= int(r["Run"])
                and day <= 5
            ]
            if opt:
                corr[r["Expt"]].append(float(r["Speed"]) - max(opt)[2] + 299000)
        vals = {s: mean(v) for s, v in corr.items()}
        yield (
            "protocol",
            "calibration",
            "Release the series means under the day-5 calibration register. Return series_ids, retained_runs and calibrated_speed.",
            "Join each experiment to its constructed instrument registration. At freeze day 5 inclusive, for each run choose the released certificate with greatest effective start run no later than that run, then highest version for the same start. Subtract its bias from the recorded Speed; a run without a released certificate is ineligible. Average corrected readings within experiment, then equally weight eligible experiment means. Report absolute speed in km/s, and numerically sorted contributing experiment strings.",
            {
                "series_ids": sorted(vals, key=int),
                "retained_runs": sum(map(len, corr.values())),
                "calibrated_speed": mean(vals.values()),
            },
            {
                "instruments.csv": table(("experiment", "device"), assignments),
                "certificates.csv": table(
                    ("device", "start_run", "version", "released_day", "bias"), cal
                ),
            },
        )

    elif name == "attenu":
        filtered = [
            r
            for r in rows
            if r["station"] and float(r["dist"]) > 0 and float(r["accel"]) > 0
        ]
        centered = []
        eligible_events = []
        for (event,), rr in group(filtered, "event").items():
            xs = [math.log(float(r["dist"])) for r in rr]
            ys = [math.log(float(r["accel"])) for r in rr]
            if len(set(xs)) < 2:
                continue
            centered.extend((x - mean(xs), y - mean(ys)) for x, y in zip(xs, ys))
            eligible_events.append(event)
        beta = sum(x * y for x, y in centered) / sum(x * x for x, y in centered)
        r2 = 1 - sum((y - beta * x) ** 2 for x, y in centered) / sum(
            y * y for x, y in centered
        )
        yield (
            "numbers",
            "attenuation",
            "Estimate the within-event attenuation slope. Return event_ids, records, log_slope, within_r2 and interpretation.",
            "Use records with known station and positive distance and acceleration. Discard events without at least two distinct retained distances. Log-transform distance and acceleration with natural logs and fit acceleration on distance with a separate intercept per event and one common slope. Use equal weight per observation. Report numerically sorted string IDs for contributing events and within-event R squared against the event-means-only model. Label the fitted distance trend decreasing, increasing or flat from the slope.",
            {
                "event_ids": sorted(eligible_events, key=int),
                "interpretation": "decreasing"
                if beta < 0
                else "increasing"
                if beta > 0
                else "flat",
                "records": len(centered),
                "log_slope": beta,
                "within_r2": r2,
            },
        )

        def attenuation_error(data):
            out = {}
            for (event,), rr in group(data, "event").items():
                rr = [
                    r
                    for r in rr
                    if r["station"] and float(r["dist"]) > 0 and float(r["accel"]) > 0
                ]
                errors = []
                for r in rr:
                    alternatives = [q for q in rr if q["station"] != r["station"]]
                    if not alternatives:
                        continue
                    at = float(r["dist"])
                    dists = [abs(math.log(float(q["dist"]) / at)) for q in alternatives]
                    m = min(dists)
                    preds = [
                        math.log(float(q["accel"]))
                        for q, d in zip(alternatives, dists)
                        if abs(d - m) <= 1e-12
                    ]
                    errors.append(abs(math.log(float(r["accel"])) - mean(preds)))
                if errors:
                    out[event] = mean(errors)
            return out

        yield (
            "program",
            "station-transfer",
            "Implement the station transfer diagnostic in the calibration note.",
            "Within each event keep identified stations with positive acceleration and distance. For each row hold out its station entirely. Predict log acceleration using the remaining record nearest in absolute log distance. Average log accelerations of tied nearest records (distances within 1e-12 of the minimum). Skip rows without a donor. Return mean absolute log prediction error by event ID string over rows with predictions; omit events without errors. Use natural logs.",
            attenuation_error,
            "accel",
        )
        # A second release for one station lacks the factor needed at the freeze.
        orders = [
            ("14", "1032"),
            ("14", "1377"),
            ("14", "1028"),
            ("15", "1051"),
            ("15", "1293"),
            ("15", "1292"),
            ("18", "1413"),
            ("18", "1445"),
        ]
        certs = [
            ("1032", 1, 1, "1.2"),
            ("1377", 1, 2, "0.9"),
            ("1028", 1, 1, "1.0"),
            ("1051", 1, 2, "0.95"),
            ("1293", 1, 2, "1.1"),
            ("1292", 1, 3, "1.2"),
            ("1292", 2, 5, ""),
            ("1292", 3, 8, "1.2"),
            ("1413", 1, 4, "1.1"),
            ("1445", 1, 5, "1.0"),
        ]
        latest = {}
        for s, rev, day, factor in certs:
            if day <= 5 and rev > latest.get(s, (0, ""))[0]:
                latest[s] = (rev, factor)
        raw = {(r["event"], r["station"]): float(r["accel"]) for r in rows}
        complete = []
        incomplete = []
        maximum = {}
        for ev in sorted({ev for ev, s in orders}, key=int):
            stations = [s for e, s in orders if e == ev]
            if all((ev, s) in raw and latest.get(s, (0, ""))[1] for s in stations):
                complete.append(ev)
                maximum[ev] = max(raw[ev, s] * float(latest[s][1]) for s in stations)
            else:
                incomplete.append(ev)
        yield (
            "protocol",
            "station-releases",
            "Audit the commissioned event panel. Return complete_events, unresolved_events, and mean_event_max over the reportable events.",
            "Use precisely the event/station pairs in the commissioning file. Join positive acceleration records to the latest signed station certificate released by day 5 (all listed certificates are signed). Highest version available controls even when a factor field is blank. A commissioned event is reportable only if every ordered pair has a measurement and usable factor. Multiply observed acceleration by the factor, take the event maximum, then average equally across reportable events. Event IDs are strings in numeric order. Commissioning and certificates are constructed records.",
            {
                "complete_events": complete,
                "unresolved_events": incomplete,
                "mean_event_max": mean(maximum.values()),
            },
            {
                "commission.csv": table(("event", "station"), orders),
                "calibration.csv": table(
                    ("station", "version", "released_day", "factor"), certs
                ),
            },
        )
    else:
        raise ValueError(name)
