import unittest

from temvera.efficiency import benchmark_efficiency
from temvera.hard_cases import hard_retrieval_fixture
from temvera.hybrid import HybridRetriever


class EfficiencyTest(unittest.TestCase):
    def test_budget_report_has_ordered_percentiles_and_sample_counts(self) -> None:
        beliefs, cases = hard_retrieval_fixture()
        rows = benchmark_efficiency(
            HybridRetriever(beliefs), cases, budgets=(1, 3), repeats=3
        )
        self.assertEqual([row.budget_items for row in rows], [1, 3])
        for row in rows:
            self.assertEqual(row.samples, len(cases) * 3)
            self.assertLessEqual(row.latency_p50_ms, row.latency_p95_ms)
            self.assertLessEqual(row.latency_p95_ms, row.latency_p99_ms)
            self.assertGreaterEqual(row.evidence_recall, 0.0)
            self.assertLessEqual(row.evidence_recall, 1.0)
        self.assertLessEqual(rows[0].context_tokens_approx, rows[1].context_tokens_approx)


if __name__ == "__main__":
    unittest.main()
