import unittest

from temvera.threats import evaluate_threats, generate_threat_scenarios


class ThreatFixtureTest(unittest.TestCase):
    def test_generation_is_seeded_and_covers_named_threats(self) -> None:
        first = generate_threat_scenarios(7)
        self.assertEqual(first, generate_threat_scenarios(7))
        self.assertNotEqual(first, generate_threat_scenarios(8))
        self.assertEqual(
            {scenario.attack_type for scenario in first if scenario.malicious},
            {"query_only_injection", "forged_front_matter", "provenance_laundering"},
        )

    def test_defense_report_separates_asr_from_utility(self) -> None:
        scenarios = generate_threat_scenarios(7)
        undefended = evaluate_threats(scenarios, defended=False)
        defended = evaluate_threats(scenarios, defended=True)
        self.assertEqual(undefended.attack_success_rate, 1.0)
        self.assertEqual(defended.attack_success_rate, 0.0)
        self.assertEqual(defended.benign_utility, 1.0)
        self.assertEqual(defended.detected_laundering, 1)


if __name__ == "__main__":
    unittest.main()
