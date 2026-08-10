import unittest

from temvera.threats import evaluate_governed_threats


class GovernedThreatTest(unittest.TestCase):
    def test_write_acceptance_and_activation_are_reported_separately(self) -> None:
        report = evaluate_governed_threats(17)
        self.assertEqual(report.attacks, 4)
        self.assertGreater(report.attack_write_acceptance_rate, 0.0)
        self.assertEqual(report.attack_activation_rate, 0.0)
        self.assertEqual(report.benign_utility, 1.0)
        self.assertGreater(report.quarantined_attacks, 0)


if __name__ == "__main__":
    unittest.main()
