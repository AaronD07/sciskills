"""Recompute evidence-packet keys from the ledger shown to participants."""
import csv
from fractions import Fraction
import io
import unittest

from benchmarks.fieldstudy.records import make


# Read separately from each packet's editorial amendment: eligible sites, the
# two publication freezes, and whether indeterminate specimens enter the rate.
SCOPES = {
    "dev": ("KLMN", ("09/18", "09/18"), False),
    "a": ("BCFHS", ("10/08", "10/20"), False),
    "b": ("DGRV", ("03/28", "03/28"), True),
    "c": ("AEJW", ("05/24", "05/24"), False),
}


def reconstruct(prompt, roster, freezes, include_indeterminate):
    start = prompt.index("ref,site,round,")
    table, _ = prompt[start:].split("\n\n", 1)
    rows = csv.DictReader(io.StringIO(table))
    live = {}
    for row in sorted(rows, key=lambda item: item["logged"]):
        site = row["site"]
        period = int(row["round"])
        if site not in roster or row["logged"] > freezes[period - 1]:
            continue
        if row["action"] == "+":
            live[site, period] = row
        elif row["action"] == "-":
            live.pop((site, period), None)
        else:
            raise ValueError(f"Unexpected ledger action: {row['action']}")

    sites = sorted(site for site in roster if (site, 1) in live and (site, 2) in live)
    output = {"sites": ",".join(sites)}
    rates = []
    for period, label in enumerate(("first", "second"), start=1):
        certificates = [live[site, period] for site in sites]
        positive = sum(int(row["positive"]) for row in certificates)
        denominator = positive + sum(int(row["negative"]) for row in certificates)
        if include_indeterminate:
            denominator += sum(int(row["indeterminate"]) for row in certificates)
        output[label + "_refs"] = ",".join(row["ref"] for row in certificates)
        output[label + "_pos"] = positive
        output[label + "_den"] = denominator
        rates.append(Fraction(positive, denominator))

    change = rates[1] - rates[0]
    output["change_pp"] = float(round(100 * change, 2))
    output["relative_change_pct"] = float(round(100 * change / rates[0], 2))
    return output


class EvidencePacketTests(unittest.TestCase):
    def test_public_ledgers_reproduce_answer_keys(self):
        for split, scope in SCOPES.items():
            with self.subTest(split=split):
                prompt, expected = make(split)
                self.assertEqual(reconstruct(prompt, *scope), expected)


if __name__ == "__main__":
    unittest.main()
