"""Independent value, design and negative controls for the matched handoffs."""

import json
import unittest

from benchmarks.research_review import everyday


# Derived from the literal packet inputs. Ordering is explicit by variant.
REFERENCES = {
    "survey-footprint": {"converted": 20 * 100**2 - 12, "literal": 20 - 12},
    "effective-tax-rate": {"basis": (13 - 18.3) * 100, "points": 13 - 18.3},
    "pressure-logger": {
        "converted": 45 * 10 / (101325 / 760) - 0.2,
        "literal": 45 - 0.2,
    },
    "earnings-scale": {"million": (-9819 - 6639) / 1000, "thousand": -9819 - 6639},
    "cost-series": {"unspecified": None, "specified": (223 / 222 - 1) * 100},
    "regional-growth": {"unspecified": None, "specified": (40 / 38.1 - 1) * 100},
    "cash-series": {"unspecified": None, "specified": (5443 / 5417 - 1) * 100},
    "profit-margin": {"unspecified": None, "specified": 18.4 - 16.2},
    "thermometer-transfer": {
        "unavailable": None,
        "available": (18.8 + 19.2 + 20.2 + 19.8) / 4 + 0.25,
    },
    "withdrawal-register": {"unavailable": None, "available": 4 - 2},
    "flow-meter": {"unavailable": None, "available": (180 + 220 + 160) / 8},
    "transect-area": {"unavailable": None, "available": (9 + 14 + 7) / 1.5},
    "collector-summary": dict.fromkeys(("working", "original"), 7.5 + 2.7 + 3.1),
    "detector-archive": dict.fromkeys(("working", "original"), 14.25 - 12.75),
    "monitor-coverage": dict.fromkeys(
        ("working", "original"), (18 + 40) / (20 + 80) * 100
    ),
    "basin-account": dict.fromkeys(("working", "original"), 450 + 210 - 125),
}


def answer(case):
    key = case["key"]
    value = REFERENCES[case["pair"]][case["variant"]]
    return {
        "state": "pending" if value is None else "complete",
        "value": value,
        "unit": key["unit"],
        "evidence": key["evidence"],
        "need": " ".join(terms[0] for terms in key.get("need", [])),
        "changes": [{**key["write"], "value": value}] if key.get("write") else [],
    }


def grade(case, submission, **extra):
    files = {**case["files"], everyday.OUTPUT: json.dumps(submission), **extra}
    return everyday.grade(case, files)


class MatchedHandoffs(unittest.TestCase):
    def setUp(self):
        self.held = everyday.cases("holdout")
        self.dev = everyday.cases("dev")

    def test_design(self):
        self.assertTrue(
            {c["pair"] for c in self.dev}.isdisjoint(c["pair"] for c in self.held)
        )
        self.assertEqual(len({c["id"] for c in self.dev + self.held}), 32)
        for rows in (self.dev, self.held):
            self.assertEqual(len(rows), 16)
            for family in {"units", "assumptions", "blockers", "scope"}:
                self.assertEqual(len([c for c in rows if c["family"] == family]), 4)

    def test_all_references_and_wrong_values(self):
        for c in self.dev + self.held:
            with self.subTest(case=c["id"]):
                a = answer(c)
                self.assertTrue(grade(c, a)["correct"])
                self.assertFalse(
                    grade(c, {**a, "value": (a["value"] or 0) + 1})["correct"]
                )

    def test_unnecessary_abstention_and_missing_disclosure(self):
        for c in self.dev + self.held:
            a = answer(c)
            if a["state"] == "pending":
                self.assertFalse(grade(c, {**a, "need": "more info"})["correct"])
                self.assertFalse(grade(c, {**a, "evidence": {}})["correct"])
            else:
                self.assertFalse(
                    grade(c, {**a, "state": "pending", "value": None})["correct"]
                )

    def test_rounded_reporting_and_case_sensitive_units(self):
        self.assertTrue(everyday._reported_number(0.45, (223 / 222 - 1) * 100, "%"))
        self.assertFalse(everyday._reported_number(0.5, (223 / 222 - 1) * 100, "%"))
        self.assertTrue(
            everyday._reported_number(3.1753, 450 * 760 / 101325 - 0.2, "torr")
        )
        self.assertFalse(everyday._reported_number(5.01, 5, "m"))
        self.assertFalse(everyday._reported_number(10**1000, 1, "m"))
        self.assertTrue(everyday._unit_matches("millimetres", "mm"))
        self.assertFalse(everyday._unit_matches("Mm", "mm"))

    def test_scope_checks_intermediate_actions_and_frozen_inputs(self):
        for c in [x for x in self.held if x["family"] == "scope"]:
            a = answer(c)
            state = json.loads(c["files"]["register.json"])
            write = a["changes"][0]
            other = next(i for i in state if i != write["record"])
            change = {**write, "record": other}
            undo = {**change, "value": state[other][write["field"]]}
            self.assertTrue(grade(c, a)["correct"])
            res = grade(c, {**a, "changes": [change, undo, write]})
            self.assertTrue(res["details"]["state_matches"])
            self.assertFalse(res["details"]["authorized"])
            self.assertFalse(grade(c, a, **{"register.json": "{}"})["correct"])
            self.assertFalse(grade(c, {**a, "changes": []})["correct"])
