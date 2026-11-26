"""Reconcile a paired instrument trial using a signed schedule and an event export."""

from fractions import Fraction
from textwrap import dedent


# Each group contains one row per scheduled specimen, in schedule order.
# The two cells in each row enumerate the attempted runs in sequence. Letters
# encode status or retry provenance; the actual case packet expands these to CSV.
CASES = {
    "dev": {
        "sites": ("Quarry", "Harbor"), "prefix": "Q", "cut": 240, "lock": 70,
        "weights": (1, 1), "withdrawals": ((4, 63), (6, 81)),
        "rows": (
            (0, "80", "93"), (0, "N A75", "T U97"), (0, "64", "N A89"),
            (0, "51", "N L91"), (0, "15", "99"), (1, "95", "83"),
            (1, "T", "64"), (1, "70", "N U96"), (1, ".", "76"),
        ),
        "settled": (((80, 93), (75, None), (64, 89), (51, None)),
                    ((95, 83), (None, 64), (70, None), (None, 76))),
    },
    "a": {
        "sites": ("Mesa", "Creek"), "prefix": "K", "cut": 216, "lock": 55,
        "weights": (3, 2), "withdrawals": ((1, 54), (7, 55)),
        "rows": (
            (0, "N U84", "72"), (0, "N A98", "28"), (0, "81", "T A91"),
            (0, "N L94", "N A68"), (0, "86", "74"), (1, "89", "83"),
            (1, "66", "."), (1, "T", "N A62"), (1, "72", "93"),
            (1, "N A85", "N W79"),
        ),
        "settled": (((None, 72), (81, None), (None, 68), (86, 74)),
                    ((89, 83), (66, None), (72, 93), (85, None))),
    },
    "b": {
        "sites": ("Delta", "Reef"), "prefix": "S", "cut": 189, "lock": 44,
        "weights": (1, 3), "withdrawals": ((0, 48), (6, 32)),
        "rows": (
            (0, "62", "N A72"), (0, "N W98", "T"), (0, "N A81", "98"),
            (0, "91", "N L95"), (0, "64", "82"), (1, "N A85", "73"),
            (1, "12", "99"), (1, "80", "T A90"), (1, ".", "N A0"),
        ),
        "settled": (((62, 72), (None, None), (81, 98), (91, None), (64, 82)),
                    ((85, 73), (80, None), (None, 0))),
    },
    "c": {
        "sites": ("North", "Ridge"), "prefix": "M", "cut": 230, "lock": 72,
        "weights": (2, 1), "withdrawals": ((3, 71), (4, 75)),
        "rows": (
            (0, "65", "N A89"), (0, "N A71", "N W96"), (0, "N U88", "79"),
            (0, "99", "40"), (1, "N L82", "T A76"), (1, "70", "67"),
            (1, ".", "85"), (1, "86", "N A0"), (1, "64", "N A74"),
        ),
        "settled": (((65, 89), (71, None), (None, 79)),
                    ((None, None), (70, 67), (None, 85), (86, 0), (64, 74))),
    },
}


def answer(groups, weights):
    """Compute estimands from independently reconciled pairs (None = failed)."""
    pairs = [pair for group in groups for pair in group]
    complete = [(a, b) for a, b in pairs if a is not None and b is not None]
    deltas = [Fraction(sum((b or 0) - (a or 0) for a, b in group), len(group))
              for group in groups]
    delta = sum(w * d for w, d in zip(weights, deltas)) / sum(weights)
    return {
        "planned": len(pairs),
        "complete": len(complete),
        "new_successes": sum(b is not None for a, b in pairs),
        "old_successes": sum(a is not None for a, b in pairs),
        "site1_delta": round(float(deltas[0]), 3),
        "site2_delta": round(float(deltas[1]), 3),
        "primary_delta": round(float(delta), 3),
        "complete_delta": round(sum(b - a for a, b in complete) / len(complete), 3),
    }


def make(split: str) -> tuple[str, dict]:
    case = CASES[split]
    sites = case["sites"]
    weights = case["weights"]
    cut = case["cut"]
    lock = case["lock"]
    prefix = case["prefix"]
    request = dedent(f"""
        The lab is checking the numbers in a methods comparison before submitting the
        instrument report. From the attached records, return the signed endpoint and
        the supplementary complete-case comparison. Return one JSON object with keys
        planned, complete, new_successes, old_successes, site1_delta, site2_delta,
        primary_delta, complete_delta. Express differences in score points, rounded
        to three decimal places. Put no other text in the answer.

        Signed analysis addendum, v3, minute {lock}
        The unit is a scheduled specimen with one slot for each method, old and new.
        A withdrawal recorded by the schedule lock (up to and including minute {lock})
        removes the specimen. Later withdrawals are recorded for operations tracking.
        Count an arm as successful when the first scheduled run returned OK by the
        export cutoff (minute {cut}, inclusive). A controller loss, NODE, qualifies
        for exactly one replacement on the same specimen and arm, provided the rerun
        ticket is signed and the replacement is on the registered method revision
        (R4) and finished by cutoff. LIMIT is the method's own resource timeout.
        Every scheduled slot that lacks an eligible OK outcome contributes zero to
        the primary score. A measured zero is a successful outcome.

        Compute each site's mean difference (new minus old) over its planned
        specimens. Site 1 is {sites[0]}, site 2 is {sites[1]}. The target site mix
        is {weights[0]} to {weights[1]} respectively. Use this mix for the primary
        difference. The supplement requests a single unweighted mean of paired
        differences among specimens with both arms successful, across both sites.
        Counts in the response refer to the locked roster across sites.

        Analyst handover, draft v2 (before addendum)
        The dashboard takes the latest nonempty score on each instrument. Its
        default difference averages completed exports, pooled across both sites.
        The dashboard includes every specimen received by the queue.

        Registered schedule
        specimen,site
    """).strip()
    roster, ledger, tickets = [], [], []
    for index, (site_index, old, new) in enumerate(case["rows"]):
        specimen = f"{prefix}{13 + index * 7}"
        roster.append(f"{specimen},{sites[site_index]}")
        for side, encoded in (("old", old), ("new", new)):
            for attempt, token in enumerate(encoded.split(), 1):
                if token == ".":
                    continue
                flag = token[0] if token[0].isalpha() else ""
                revision = "R3" if flag == "W" else "R4"
                status = {"T": "LIMIT", "N": "NODE"}.get(flag, "OK")
                value = token[len(flag):] if status == "OK" else ""
                end = cut - 32 + index if attempt == 1 else cut - index
                if flag == "L":
                    end = cut + 1
                ledger.append(f"{specimen},{side},{attempt},{revision},{end},{status},{value}")
                if attempt == 2 and flag != "U":
                    tickets.append(f"{specimen},{side},2,signed")
    # The export is grouped by arm and completion time, not schedule order.
    ledger.sort(key=lambda s: (s.split(",")[1], int(s.split(",")[4]), s.split(",")[0]))
    withdraw = [f"{prefix}{13 + index * 7},{time}" for index, time in case["withdrawals"]]
    extra = f"{prefix}1000"
    ledger.extend([f"{extra},new,1,R4,{cut - 2},OK,98", f"{extra},old,1,R4,{cut - 3},OK,62"])
    documents = [
        request, *roster, "", "Withdrawal register", "specimen,recorded_minute", *withdraw,
        "", "Controller recovery register", "specimen,arm,attempt,authorization", *tickets,
        "", "Queue export", "specimen,arm,attempt,revision,finished_minute,status,score", *ledger,
    ]
    return "\n".join(documents), answer(case["settled"], weights)
