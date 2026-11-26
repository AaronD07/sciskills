"""Generate frozen calibration-ledger packets and their reference endpoints."""

import csv
from io import StringIO
from random import Random
from fractions import Fraction


# Campaigns share an archive schema. Their signed reporting amendments differ.
CAMPAIGNS = {
    "d": ("Estuary conductivity probes", "E", 361, 9, (22, 22), False, "pooled"),
    "e": ("Stack opacity monitors", "M", 713, 14, (17, 26), True, "station mean"),
    "f": ("Particulate sampler flow audit", "F", 839, 17, (21, 29), False, "pooled"),
}
ROUNDS = ("before", "after")


def csv_text(header, rows):
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def records(prefix, seed):
    rng = Random(seed)
    roster, schedule, certificates = [], [], []
    for index in range(1, 29):
        station = f"{prefix}{index:02d}"
        opening = rng.choice([1, 2, 3, 7, 11, 15])
        last = rng.choice([12, 18, 31, 31, 31])
        roster.append((station, "production" if index % 7 else "pilot", opening, last))
        channels = ("low", "high", "span") if index % 3 == 0 else ("low", "high")
        for round_index, period in enumerate(ROUNDS):
            for channel_index, channel in enumerate(channels):
                schedule.append((station, period, channel))
                # Returns contain independently timestamped releases. Some late
                # receipts describe earlier work. Arrival order has no precedence.
                base_day = rng.randint(4, 10) if round_index == 0 else rng.randint(12, 17)
                issue2 = base_day + rng.randint(2, 7)
                issues = (base_day, issue2, issue2 if index % 4 == 0 else issue2 + rng.randint(1, 5))
                for seq, issue in enumerate(issues, 1):
                    received = issue + rng.choice([0, 1, 2, 4, 7, 10])
                    code = index + seq * 5 + round_index * 2 + channel_index
                    withdrawn = seq >= 2 and code % 13 == 0
                    passed = rng.randint(8, 33)
                    failed = rng.randint(2, 13)
                    unreadable = rng.randint(0, 6)
                    counts = ("", "", "") if withdrawn else (passed, failed, unreadable)
                    certificates.append((station, period, channel, seq, issue, received,
                                         "withdraw" if withdrawn else "certify", *counts))
        # Engineering checks are present in the archive but outside the field schedule.
        certificates.append((station, "after", "bench", 1, 13, 14, "certify", 75, 0, 0))
    for rows in (roster, schedule, certificates):
        rng.shuffle(rows)
    return roster, schedule, certificates


def rounded(value):
    return round(float(value), 3)


def endpoint(roster, schedule, versions, anchor, cutoffs, include_unreadable, aggregation):
    eligible = {station for station, group, start, stop in roster
                if group == "production" and start <= anchor <= stop}
    scheduled = {(s, period, chan) for s, period, chan in schedule if s in eligible}
    selected = {}
    by_round = dict(zip(ROUNDS, cutoffs))
    for station, period, chan, edition, issue, received, action, passed, failed, unreadable in versions:
        key = station, period, chan
        if key not in scheduled or max(issue, received) > by_round[period]:
            continue
        rank = issue, edition
        if key not in selected or rank > selected[key][0]:
            selected[key] = (rank, action, passed, failed, unreadable)
    panel = {s for s in eligible if all(k in selected and selected[k][1] == "certify"
                                        for k in scheduled if k[0] == s)}
    totals = {}
    rates = {}
    for period in ROUNDS:
        counts = []
        for s in sorted(panel):
            numerator = denominator = 0
            for key in scheduled:
                if key[:2] == (s, period):
                    _, _, passed, failed, unreadable = selected[key]
                    numerator += passed
                    denominator += passed + failed + (unreadable if include_unreadable else 0)
            counts.append((numerator, denominator))
        num = sum(x for x, _ in counts)
        den = sum(y for _, y in counts)
        totals[period] = (num, den)
        rates[period] = (Fraction(num, den) if aggregation == "pooled" else
                         sum(Fraction(x, y) for x, y in counts) / len(counts))
    return {
        "roster_count": len(eligible), "paired_count": len(panel),
        "panel": ",".join(sorted(panel)),
        "before_pass": totals["before"][0], "before_den": totals["before"][1],
        "after_pass": totals["after"][0], "after_den": totals["after"][1],
        "before_pct": rounded(100 * rates["before"]), "after_pct": rounded(100 * rates["after"]),
        "change_pp": rounded(100 * (rates["after"] - rates["before"])),
        "relative_change_pct": rounded(100 * (rates["after"] / rates["before"] - 1)),
    }


def make(split: str) -> tuple[dict[str, str], dict]:
    title, prefix, seed, anchor, cuts, include_unreadable, aggregation = CAMPAIGNS[split]
    roster, schedule, versions = records(prefix, seed)
    denom = ("Every scheduled reading attempt, including an unreadable instrument return, counts."
             if include_unreadable else
             "The denominator is determinate readings, consisting of passed and failed readings. Unreadable returns are excluded.")
    method = ("For each round use one pooled fraction across the paired stations."
              if aggregation == "pooled" else
              "The endpoint is the arithmetic mean of the individual station pass fractions, with equal weight per station. Within each station pool its scheduled channels. Still supply the raw pooled counts as audit fields.")
    task = f"""# {title}

Reconstruct the paired field calibration endpoint for the network methods note. Three CSV extracts accompany the signed amendment below. Campaign records use integer day numbers. All listed day cutoffs are inclusive.

**Population.** Use production stations in service on day {anchor}. The first and last service days in stations.csv both count. Keep a station in the paired panel only when it has an active certificate for every channel scheduled for that station in both rounds. schedule.csv is the field schedule. Auxiliary engineering checks also appear in the export.

**Releases.** Use the before-round archive as of day {cuts[0]} and the after-round archive as of day {cuts[1]}. A release is available when both its issue day and archive receipt day are within that round's cutoff. Among available releases for a station, round and channel, use the latest by issue day, then the largest numeric edition for a same-day tie. The selected action governs: a withdrawal cancels the channel certificate; a later certification can reinstate it. The archive export is unordered.

**Estimand.** A certification gives three disjoint counts: readings that passed, readings that failed, and unreadable returns. {denom} {method} Compare after with before. Compute percentages, percentage-point change and relative percentage change from the unrounded fractions. Round only those final four quantities to three decimal places.

Return one flat JSON object. Fields are roster_count (eligible stations before panel exclusions), paired_count, panel (station IDs in ascending alphabetical order, comma-separated without spaces), before_pass, before_den, after_pass, after_den (raw counts from paired stations), before_pct, after_pct, change_pp and relative_change_pct. Return the numeric fields as JSON numbers. Use local computation if helpful.
"""
    files = {
        "TASK.md": task,
        "stations.csv": csv_text(("station", "use", "first_day", "last_day"), roster),
        "schedule.csv": csv_text(("station", "round", "channel"), schedule),
        "certificates.csv": csv_text(
            ("station", "round", "channel", "edition", "issued", "received", "action",
             "passed", "failed", "unreadable"), versions),
    }
    return files, endpoint(roster, schedule, versions, anchor, cuts, include_unreadable, aggregation)
