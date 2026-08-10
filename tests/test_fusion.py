import unittest

from temvera.fusion import compare_fusion


class FusionTest(unittest.TestCase):
    def test_calibration_uses_disjoint_variants_and_is_deterministic(self) -> None:
        result = compare_fusion((0, 1, 2, 3), (100, 101, 102, 103))
        self.assertEqual(result, compare_fusion((0, 1, 2, 3), (100, 101, 102, 103)))
        self.assertEqual(result.development_examples, 16)
        self.assertEqual(result.test_examples, 16)
        self.assertGreaterEqual(result.fixed_test_recall_at_budget, 0.0)
        self.assertLessEqual(result.fixed_test_recall_at_budget, 1.0)

    def test_overlap_between_development_and_test_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compare_fusion((0, 1), (1, 2))


if __name__ == "__main__":
    unittest.main()
