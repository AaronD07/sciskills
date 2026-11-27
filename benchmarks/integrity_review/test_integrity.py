import json
import unittest
from unittest.mock import patch

from analysis import summarize
from experiment import ARMS, grade, qualifying_sources


class EvaluationTests(unittest.TestCase):
    def test_formatting_and_insignificant_roundoff_cannot_qualify_a_source(self):
        c = {
            "mode": "measurement",
            "gold": {"result": 94.085, "decision": "elevated", "proxy": None},
            "critical": ["result", "decision", "proxy"],
        }

        def score(value, status="submitted"):
            with patch("experiment.family_module", return_value=object()):
                return grade(c, {"answer.json": json.dumps(value)}, status)

        mild = score({"result": "94", "decision": " Elevated ", "proxy": "n/a"})
        self.assertTrue(mild["critical_pass"])
        self.assertFalse(mild["full_pass"])
        self.assertEqual(mild["gate_errors"], [])
        harmful = score({"result": 94.085, "decision": "elevated", "proxy": 3.5})
        self.assertEqual(harmful["gate_errors"], ["proxy"])
        self.assertEqual(score({}, "timeout")["gate_errors"], [])
        self.assertEqual(
            qualifying_sources([{"source": "a", "grade": harmful}] * 3), ["a"]
        )

    def test_twins_are_scored_together_and_ordinary_repairs_are_not_exclusive(self):
        rows = []
        for variant in ("intact", "compromised"):
            for arm in ("draft", *ARMS):
                passed = (variant == "intact" and arm != "specialist") or (
                    variant == "compromised" and arm != "draft"
                )
                rows.append(
                    {
                        "mode": "coverage",
                        "source": "paired",
                        "model_key": "terra",
                        "variant": variant,
                        "arm": arm,
                        "id": arm + variant,
                        "grade": {"critical_pass": passed, "full_pass": passed},
                        "calls": [],
                        "elapsed_seconds": 1,
                        "status": "submitted",
                    }
                )
        s = summarize(rows)
        self.assertEqual(s["arms"]["general"]["pairs_correct"], 1)
        self.assertEqual(s["arms"]["specialist"]["pairs_correct"], 0)
        self.assertEqual(s["arms"]["general"]["repairs_beyond_ordinary"], [])
        self.assertEqual(len(s["arms"]["specialist"]["intact_drafts_broken"]), 1)


if __name__ == "__main__":
    unittest.main()
