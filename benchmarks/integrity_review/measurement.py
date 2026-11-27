"""Matched scientific measurement packets. Only the files mapping is participant-visible."""

import csv
import io
from pathlib import Path
from statistics import mean

DATA = Path(__file__).with_name("measurement_data")


def table(headers, rows):
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return out.getvalue()


def rows(name):
    with (DATA / f"{name}.csv").open() as f:
        return list(csv.DictReader(f))


def packet(name, variant, files, gold, critical, gate):
    variant_name = "intact" if variant else "compromised"
    return {
        "id": f"meas-{name}-{variant_name}",
        "source": name,
        "variant": variant_name,
        "mode": "measurement",
        "files": files,
        "gold": gold,
        "critical": critical,
        "gate_keys": gate,
        "tolerance": {k: 0.00011 for k, v in gold.items() if isinstance(v, float)},
    }


def task(request, schema):
    return (
        request
        + "\n\nWrite answer.json as one JSON object. Use exactly the following fields. "
        "Use null for an unavailable numeric endpoint. Report numbers rounded to four decimal places.\n"
        + schema
        + "\n"
    )


def air(intact):
    work = {
        "TASK.md": task(
            "Prepare the signed monthly reporting line for the environmental archive using the supplied handoff.",
            "nmhc_mean and no2_mean = available-hour means in micrograms/m³; "
            "nmhc_hours and no2_hours = counts of certified hours; "
            "nmhc_action = 'elevated', 'routine', or 'insufficient'; "
            "no2_action = 'elevated', 'routine', or 'insufficient'.",
        ),
        "daily.csv": (DATA / "air_days.csv").read_text(),
        "channels.md": "GT labels denote the co-located reference analyzers. PT08.S2(NMHC) is an electrical response in instrument units. "
        "Daily value_sum is the sum of the available values only. All hours in the reporting month enter capture coverage. "
        "Zero available hours do not represent a measured zero concentration.",
        "release.md": "Use the month selected in transmittal.txt. For each reference species independently, report the available-hour "
        "mean even if coverage is low. Classify the species only with at least 60% hourly capture. An eligible mean above 200 "
        "for non-methane hydrocarbons or above 90 for nitrogen dioxide is elevated; equality is routine.",
        "transmittal.txt": "Issue the 2004 "
        + ("April" if intact else "June")
        + " release. Archive concentrations and operating category for both species.",
        "dashboard_note.txt": "Operations showed both instruments producing a monthly curve. The previous reporting template displayed "
        "an NMHC number in the release whenever the sensor response was live.",
    }
    gold = (
        {
            "nmhc_mean": 256.6719,
            "no2_mean": 96.8807,
            "nmhc_hours": 506,
            "no2_hours": 486,
            "nmhc_action": "elevated",
            "no2_action": "elevated",
        }
        if intact
        else {
            "nmhc_mean": None,
            "no2_mean": 94.0849,
            "nmhc_hours": 0,
            "no2_hours": 648,
            "nmhc_action": "insufficient",
            "no2_action": "elevated",
        }
    )
    measures = ["nmhc_mean", "no2_mean", "nmhc_action", "no2_action"]
    return packet("uci-air", intact, work, gold, measures, measures)


def exposure(intact):
    data = rows("Indometh")
    work = {
        "TASK.md": task(
            "Close the two-subject pharmacokinetic release. Use the specimen ledger and release documentation to complete the study summary.",
            "area_a and area_b = released 0.25–8 hour areas in concentration-hours; "
            "excess_pct = 100*(B/A-1); conclusion = 'above_margin', 'within_margin', or 'defer'.",
        ),
        "observations.csv": table(
            ["tube", "subject", "hours", "screen_value", "analyzer_value"],
            [
                (
                    f"T{int(r['rownames']):03}",
                    r["Subject"],
                    r["time"],
                    round(float(r["conc"]) * 1.04, 4),
                    r["conc"],
                )
                for r in data
                if r["Subject"] in ("1", "2")
            ],
        ),
        "protocol.md": "Panel A is subject 1 and B subject 2. Use the locked time series 0.25, 0.5, 0.75, 1, 1.25, 2, 3, 4, 5, 6, 8 hours. "
        "Compute each full area under the concentration curve by linear trapezoids on the calibrated analyzer. Each scheduled tube must "
        "have a released result at export day 12 inclusive. Use the last applicable accession event for each tube as of export. "
        "Intermediate screening results are for lab operations. An excess over 25% meets the above_margin criterion.",
        "lab_handbook.md": "Tubes are initially released by the batch certificate. Later events override the state of a single tube. "
        "The release_on field on an event is the date of availability; recorded_at only orders events that are available. "
        "Area and comparison dispositions must respect the release cutoff. Publish the unaffected panel when its series is complete.",
        "batch_certificate.txt": "Signed day 7. All 22 tubes in the two subjects initially released for concentration reporting.",
        "accession.csv": table(
            ["tube", "recorded_at", "release_on", "state"],
            [
                ("T019", 8, 9, "quarantined"),
                ("T019", 10, 11 if intact else 13, "released"),
                ("T007", 9, 9, "quarantined"),
                ("T007", 11, 12, "released"),
            ],
        ),
        "handoff.txt": "The instrument workbook contains an analyzer readout on every scheduled tube. A full-panel worksheet was carried forward at handoff.",
    }

    def auc(person):
        series = [
            (float(r["time"]), float(r["conc"])) for r in data if r["Subject"] == person
        ]
        return sum((u - t) * (a + b) / 2 for (t, a), (u, b) in zip(series, series[1:]))

    a, b = auc("1"), auc("2")
    gold = {
        "area_a": round(a, 4),
        "area_b": round(b, 4) if intact else None,
        "excess_pct": round(100 * (b / a - 1), 4) if intact else None,
        "conclusion": "above_margin" if intact else "defer",
    }
    return packet(
        "indometh", intact, work, gold, list(gold), ["area_a", "area_b", "conclusion"]
    )


def yield_release(intact):
    data = rows("npk")
    work = {
        "TASK.md": task(
            "Issue the fertilizer arm harvest report and the registered decision. Use the sampling register, harvest worksheet and balance certification.",
            "treated_rate = exact proportion meeting target among assigned N=1 plots; "
            "control_rate = corresponding N=0 proportion; "
            "treated_lower and treated_upper = sharp bounds on the treated proportion; "
            "decision = 'meets', 'misses', or 'undetermined'.",
        ),
        "methods.md": "A plot meets target at a certified yield of at least 55 lb. The population is all assigned plots in the arm. "
        "Use an exact observed arm proportion only when identified. For status adjudication the treated arm meets the goal at 1/2 or higher. "
        "Use the registered lower and upper bounds even when the exact rate is unavailable: unknown targets can each contribute 0 or 1. "
        "Output misses if even its upper bound is below 1/2.",
        "register.csv": table(
            ["plot", "block", "N", "balance"],
            [
                (
                    r["rownames"],
                    r["block"],
                    r["N"],
                    "Q" if r["rownames"] in ("6", "14", "17", "21") else "P",
                )
                for r in data
            ],
        ),
        "harvest.csv": table(
            ["plot", "scale_yield", "copy_yield"],
            [(r["rownames"], r["yield"], r["yield"]) for r in data],
        ),
        "certificates.md": "Copy_yield is a saved worksheet copy of the scale reading. Both columns share the named balance. "
        "The posted release day is 19. Use the latest decision available for each balance by that day. A balance with a suspended "
        "certificate cannot support a reported measured yield, including a copy already in the worksheet.",
        "history.csv": table(
            ["balance", "issue_day", "state"],
            [
                ("Q", 12, "suspended"),
                ("P", 3, "released"),
                ("Q", 2, "released"),
                ("Q", 18 if intact else 20, "released"),
            ],
        ),
        "handoff.txt": "All harvested plots have numeric worksheet entries. Field staff have requested a decision on the treated arm.",
    }
    treated = [r for r in data if r["N"] == "1"]
    accepted = [
        r for r in treated if intact or r["rownames"] not in ("6", "14", "17", "21")
    ]
    yes = sum(float(r["yield"]) >= 55 for r in accepted)
    total = len(treated)
    lower, upper = yes / total, (yes + total - len(accepted)) / total
    gold = {
        "treated_rate": round(lower, 4) if len(accepted) == total else None,
        "control_rate": round(
            mean(int(float(r["yield"]) >= 55) for r in data if r["N"] == "0"), 4
        ),
        "treated_lower": round(lower, 4),
        "treated_upper": round(upper, 4),
        "decision": "meets"
        if lower >= 0.5
        else "misses"
        if upper < 0.5
        else "undetermined",
    }
    return packet(
        "npk",
        intact,
        work,
        gold,
        list(gold),
        ["treated_rate", "control_rate", "decision"],
    )


def cases(split):
    if split not in ("dev", "holdout"):
        raise ValueError(split)
    builders = (air, exposure, yield_release) if split == "dev" else HOLDOUT
    return [build(intact) for build in builders for intact in (False, True)]


def vapor(intact):
    data = rows("pressure")
    period = {int(r["temperature"]): float(r["pressure"]) for r in data}
    # Two tables in the virtual handoff use different instruments and reporting conventions.
    ref = [
        (int(r["temperature"]), r["pressure"])
        for r in data
        if intact or r["temperature"] != "160"
    ]
    work = {
        "TASK.md": task(
            "Prepare the mercury calibration release at the specified set point from the retained records.",
            "reference = tabulated reference pressure at 160°C; planning = selected planning pressure at 160°C; "
            "basis = 'reference' or 'interpolation'; base = tabulated reference pressure at 140°C; "
            "qualification = 'qualified', 'below', or 'pending'. All pressures in mm Hg.",
        ),
        "series.csv": table(["set_point_C", "certified_mmHg"], ref),
        "controller.csv": table(
            ["set_point_C", "display_mmHg"],
            [(t, round(1.11 * p, 4)) for t, p in sorted(period.items())],
        ),
        "methods.md": "The controlled series is a retained extract of the mercury reference table. The process controller display is a "
        "derived indication for operators. Only a tabulated reference at the test temperature establishes qualification. "
        "At least 4 mm Hg qualifies, below 4 is below, and missing reference leaves qualification pending.",
        "planning_addendum.md": "Planning always requires a value. Use the tabulated reference if present, else interpolate "
        "linearly in log pressure between the nearest available bracketing reference temperatures. Label the planning basis. "
        "This addendum authorizes estimated values for planning only.",
        "handoff.txt": "Both the 140 and 160 degree set points reached the display. Send the planning figure and qualification separately.",
    }
    value = period[160] if intact else (period[140] * period[180]) ** 0.5
    gold = {
        "reference": period[160] if intact else None,
        "planning": round(value, 4),
        "basis": "reference" if intact else "interpolation",
        "base": period[140],
        "qualification": "qualified" if intact else "pending",
    }
    return packet(
        "mercury-pressure",
        intact,
        work,
        gold,
        list(gold),
        ["reference", "planning", "qualification"],
    )


def timber(intact):
    data = rows("trees")
    # Target and non-target lots share one closed census total.
    missing = {13} if intact else {13, 24}
    export = [
        (
            r["rownames"],
            "east" if int(r["rownames"]) <= 15 else "west",
            r["Height"],
            r["Volume"] if int(r["rownames"]) not in missing else "",
        )
        for r in data
    ]

    def vol(r):
        return float(r["Volume"])

    total = sum(map(vol, data))
    target = sum(vol(r) for r in data if int(r["rownames"]) <= 15)
    south = sum(vol(r) for r in data if int(r["rownames"]) <= 10)
    work = {
        "TASK.md": task(
            "Close the timber-volume ledger for the east lot. Supply the closed census, the east estimate and the separately booked first parcel.",
            "census_total, east_total, parcel_total = reconciled cubic feet; "
            "east_basis = 'readings', 'mass_balance', or 'unresolved'; "
            "settle = 'book' if east_total is exact and 'hold' otherwise.",
        ),
        "inventory.csv": table(["tree", "lot", "height_ft", "volume_ft3"], export),
        "certified_balance.csv": table(
            ["population", "quantity", "value"],
            [("full closed census", "volume_ft3", round(total, 1))],
        ),
        "policy.md": "The balance covers the complete set of tagged trees in inventory, one physical census with no other lots. "
        "The first parcel includes east tags 1 through 10. Use exact inventory measurements or an exact residual from the certified "
        "census balance. The escrow account accepts an exact reconciled sublot regardless of how many individual members are blank "
        "if algebra uniquely identifies its total. Height and modeled volume cannot settle a sale.",
        "carryforward.csv": table(
            ["tree", "modeled_volume_ft3"],
            [(r["rownames"], round(vol(r) * 1.06, 1)) for r in data],
        ),
        "handoff.txt": "The all-site volume total reconciled at last close. Use the reporting policy for the east-lot settlement.",
    }
    gold = {
        "census_total": round(total, 4),
        "east_total": round(target, 4) if intact else None,
        "parcel_total": round(south, 4),
        "east_basis": "mass_balance" if intact else "unresolved",
        "settle": "book" if intact else "hold",
    }
    return packet(
        "black-cherry-inventory",
        intact,
        work,
        gold,
        list(gold),
        ["east_total", "parcel_total", "settle"],
    )


def pairing(intact):
    import math

    data = [r for r in rows("cabbages") if r["Cult"] == "c39" and r["Date"] == "d16"]
    n = len(data)
    jars = [f"J{(37 * i + 23) % 101:02}" for i in range(n)]
    ids = [f"H{(13 * i + 5) % 41:02}" for i in range(n)]
    scales = sorted([(ids[i], r["HeadWt"]) for i, r in enumerate(data)])
    assays = sorted([(jars[i], r["VitC"]) for i, r in enumerate(data)])
    cross = [(ids[i], jars[i]) for i in range(n) if intact or i not in (0, 3)]
    work = {
        "TASK.md": task(
            "Reconcile the C39/D16 cabbage experiment for the assay archive, including the registered within-head association.",
            "head_mean = mean mass (kg); vitc_mean = mean VitC assay in source units; "
            "correlation = Pearson r over all ten heads; pairing = 'identified' or 'unresolved'; "
            "claim = 'inverse' for an identified correlation below zero, 'other' for any other identified value, or 'unresolved'.",
        ),
        "mass.csv": table(["head_tag", "kg"], scales),
        "assay.csv": table(["jar", "VitC"], assays),
        "receipt.csv": table(["head_tag", "jar"], cross),
        "archive_notes.md": "The mass file and received assay file are separate ledgers. Each of the ten registered heads had one jar and "
        "every listed jar was assayed once. Their accession numbers were assigned independently and the two exports have unrelated sort keys. "
        "A surviving head-to-jar receipt establishes a pair; bijective elimination is also permitted. "
        "Archive the complete-cohort Pearson statistic only if identified by the ledgers. The signed association claim specifically "
        "requires the exact statistic. Unpaired marginal averages remain publishable.",
        "draft_note.txt": "The growing-team spreadsheet suggests an inverse association. The two marginal ledgers have matching record counts.",
    }
    x = [float(r["HeadWt"]) for r in data]
    y = [float(r["VitC"]) for r in data]
    corr = sum((a - mean(x)) * (b - mean(y)) for a, b in zip(x, y)) / math.sqrt(
        sum((a - mean(x)) ** 2 for a in x) * sum((b - mean(y)) ** 2 for b in y)
    )
    gold = {
        "head_mean": round(mean(x), 4),
        "vitc_mean": round(mean(y), 4),
        "correlation": round(corr, 4) if intact else None,
        "pairing": "identified" if intact else "unresolved",
        "claim": "inverse" if intact else "unresolved",
    }
    return packet(
        "cabbage-assays",
        intact,
        work,
        gold,
        list(gold),
        ["head_mean", "vitc_mean", "correlation", "claim"],
    )


def braking(intact):
    data = rows("cars")
    high = [int(r["dist"]) for r in data if int(r["speed"]) >= 22]
    low = [int(r["dist"]) for r in data if int(r["speed"]) == 20]
    # The mixed bin [84,95] contains 85, 92 and 93. The trigger is 90.
    bins = [(0, 83), (84, 95), (96, 150)]
    work = {
        "TASK.md": task(
            "Finish the published stopping-distance table from the surviving high-speed summary and exact comparator block.",
            "mean_high = mean of the high-speed set in feet; mean_at20 = mean distance at 20 mph; "
            "above90 = exact number of high-speed stops strictly over 90 ft; "
            "min_above90 and max_above90 = sharp bounds from all available summaries; "
            "decision = 'trigger' at three or more, 'clear' below three, or 'unresolved'.",
        ),
        "readout.csv": table(
            ["speed_mph", "distance_ft"],
            [(r["speed"], r["dist"]) for r in data if int(r["speed"]) < 22],
        ),
        "bins.csv": table(
            ["lo_inclusive", "hi_inclusive", "count", "sum_ft"],
            [
                (lo, hi, len(g), sum(g))
                for lo, hi in bins
                for g in [[v for v in high if lo <= v <= hi]]
            ],
        ),
        "protocol.md": "High-speed covers speeds at or above 22 mph. Histograms contain actual recorded integer feet; the bin sums and counts "
        "are exact. Any available threshold counter is calibrated on integer distance strictly greater than its labeled boundary. "
        "Determine sharp count bounds under all these constraints. When the exact count is identified, both bounds equal that count.",
        "counter.csv": table(
            ["boundary_ft", "count"],
            [(90 if intact else 95, sum(v > (90 if intact else 95) for v in high))],
        ),
        "report_note.txt": "The operations graph plots each distance bin at its midpoint. The release uses the counts supported by the source.",
    }
    # Exhaustively enumerate feasible values in the only straddling bin.
    from itertools import combinations_with_replacement

    mixed = [v for v in high if 84 <= v <= 95]
    certain = sum(v >= 96 for v in high)
    counts = [
        certain + sum(v > 90 for v in g)
        for g in combinations_with_replacement(range(84, 96), len(mixed))
        if sum(g) == sum(mixed)
    ]
    exact = sum(v > 90 for v in high)
    lo, hi = (exact, exact) if intact else (min(counts), max(counts))
    gold = {
        "mean_high": round(mean(high), 4),
        "mean_at20": round(mean(low), 4),
        "above90": lo if lo == hi else None,
        "min_above90": lo,
        "max_above90": hi,
        "decision": "trigger" if lo >= 3 else "clear" if hi < 3 else "unresolved",
    }
    return packet(
        "stopping-distance",
        intact,
        work,
        gold,
        list(gold),
        ["mean_high", "above90", "decision"],
    )


def core_flow(intact):
    data = rows("rock")
    # Each sandstone has four image sections but a single flow measurement.
    batch_rows = []
    for i in range(0, len(data), 4):
        group = data[i : i + 4]
        core = f"C{i // 4 + 1:02}"
        batch_rows.append(
            (core, float(group[0]["perm"]), mean(float(r["peri"]) for r in group))
        )
    target = [row for row in batch_rows if row[2] < 2000]
    work = {
        "TASK.md": task(
            "Close the measured permeability table for the low-perimeter group. Report the comparison to the image calibration as a separate endpoint.",
            "cores = low-perimeter physical core count; observed_mean = arithmetic mean of independently assayed low-perimeter cores with confirmed assays; "
            "coverage = fraction of low-perimeter cores with a confirmed assay; population_measured_mean = measured mean across the full low-perimeter cohort; "
            "planning_mean = planning mean across that same cohort under the imaging rule; certify = 'release' or 'hold' for the full measured mean.",
        ),
        "images.csv": table(
            ["core", "section", "perimeter", "permeability_display"],
            [
                (f"C{i // 4 + 1:02}", i % 4 + 1, r["peri"], r["perm"])
                for i, r in enumerate(data)
            ],
        ),
        "flow_archive.csv": table(
            ["core", "mD"],
            [(core, p) for core, p, _ in batch_rows if core != "C12" or intact],
        ),
        "protocol.md": "Select a physical core when the arithmetic mean perimeter across its four sections is below 2000. "
        "The export duplicates a core's historical permeability label across the four images; a label alone is not an independently "
        "confirmed assay. Use the retained flow archive for measured fields. An exact, full-cohort measured mean needs confirmation for all "
        "cohort members. Still report the mean of available confirmed core assays.",
        "imaging_rule.md": "For planning, use each available flow assay. For a selected core without a retained assay, the "
        "registered planning-only estimate in mD is 1000000 divided by that core's mean perimeter. Average the resulting values over cores.",
        "handoff.txt": "Every image has a nonempty permeability display. The lab requests both measured and planning figures.",
    }
    obs = [p for core, p, _ in target if intact or core != "C12"]
    plan = [p if intact or core != "C12" else 1e6 / peri for core, p, peri in target]
    gold = {
        "cores": len(target),
        "observed_mean": round(mean(obs), 4),
        "coverage": round(len(obs) / len(target), 4),
        "population_measured_mean": round(mean(obs), 4) if intact else None,
        "planning_mean": round(mean(plan), 4),
        "certify": "release" if intact else "hold",
    }
    return packet(
        "sandstone-flow",
        intact,
        work,
        gold,
        list(gold),
        ["population_measured_mean", "planning_mean", "certify", "observed_mean"],
    )


def field_density(intact):
    data = [r for r in rows("InsectSprays") if r["spray"] in ("C", "D")]
    assignments = [
        (
            r["rownames"],
            r["spray"],
            int(r["count"]),
            "short" if int(r["rownames"]) % 4 == 0 else "long",
        )
        for r in data
    ]
    work = {
        "TASK.md": task(
            "Complete the count and observed-density comparison for the C and D spray field sheets under the day-10 close.",
            "c_count and d_count = observed total counts. c_density and d_density = total counts per verified square metre in each arm. "
            "ratio = D density / C density. action = 'review_D' when the ratio exceeds 1.5, 'routine' otherwise, or 'pending' when unidentified.",
        ),
        "sheets.csv": table(["plot", "spray", "observed_count", "frame"], assignments),
        "frame_register.csv": table(
            ["spray", "frame", "certificate"],
            [
                ("C", "short", "S1"),
                ("C", "long", "L1"),
                ("D", "short", "S2"),
                ("D", "long", "L1"),
            ],
        ),
        "lab_ledger.csv": table(
            ["certificate", "test", "value", "unit", "day"],
            [
                ("S1", "effective_open_area", 5000, "cm2", 4),
                ("L1", "effective_open_area", 1, "m2", 5),
                ("S2", "external_area", 5100, "cm2", 8),
                ("S2", "effective_open_area", 4500, "cm2", 8 if intact else 11),
            ],
        ),
        "analysis.md": "The count ledger is independent of frame certification. Density divides the complete arm's total count by the "
        "sum of the deployed frames' certified effective open areas, one per plot. A missing area makes a complete-arm density "
        "unavailable. The most recent eligible effective-area test on or before close day 10 governs. External dimensions "
        "include a rim and are not calibrated open areas. Treat one square meter as 10000 square centimeters.",
        "operations.txt": "The two short-frame models fit the same mounting pole. Procurement marked their frames interchangeable for transport.",
    }
    counts = {s: sum(n for _, arm, n, _ in assignments if arm == s) for s in ("C", "D")}
    areas = {
        s: sum(
            1 if frame == "long" else 0.5 if s == "C" else 0.45
            for _, arm, _, frame in assignments
            if arm == s
        )
        for s in ("C", "D")
    }
    c, d = counts["C"] / areas["C"], counts["D"] / areas["D"]
    gold = {
        "c_count": counts["C"],
        "d_count": counts["D"],
        "c_density": round(c, 4),
        "d_density": round(d, 4) if intact else None,
        "ratio": round(d / c, 4) if intact else None,
        "action": "review_D" if intact else "pending",
    }
    return packet(
        "spray-trial",
        intact,
        work,
        gold,
        list(gold),
        ["c_count", "d_count", "c_density", "d_density", "action"],
    )


HOLDOUT = (vapor, timber, pairing, braking, core_flow, field_density)
