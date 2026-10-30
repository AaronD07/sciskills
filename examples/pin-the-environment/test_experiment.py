import unittest
from experiment import estimate_pi


class ReproducibilityTests(unittest.TestCase):
    def test_same_seed_same_result(self):
        self.assertEqual(estimate_pi(1000, 42), estimate_pi(1000, 42))

    def test_plausible_estimate(self):
        self.assertTrue(2.5 < estimate_pi(10000, 42) < 3.7)

    def test_invalid_sample_count(self):
        with self.assertRaises(ValueError):
            estimate_pi(0, 42)


if __name__ == "__main__":
    unittest.main()
