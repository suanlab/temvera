import unittest

from temvera.hard_cases import hard_retrieval_fixture
from temvera.hybrid import CHANNELS, HybridRetriever, hard_channel_ablation


EXPECTED_CHANNEL = {
    "exact_identifier": "exact",
    "lexical_code": "lexical",
    "vector_synonym": "vector",
    "temporal_version": "temporal",
    "graph_derivation": "graph",
}


class HardCaseTest(unittest.TestCase):
    def test_each_category_is_recalled_with_all_channels(self) -> None:
        beliefs, cases = hard_retrieval_fixture()
        rows = hard_channel_ablation(HybridRetriever(beliefs), cases)
        full = [row for row in rows if row.removed_channel is None]
        self.assertEqual(len(full), len(EXPECTED_CHANNEL))
        self.assertTrue(all(row.recalled for row in full))

    def test_each_category_fails_when_its_required_channel_is_removed(self) -> None:
        beliefs, cases = hard_retrieval_fixture()
        rows = hard_channel_ablation(HybridRetriever(beliefs), cases)
        for category, required in EXPECTED_CHANNEL.items():
            row = next(
                item
                for item in rows
                if item.category == category and item.removed_channel == required
            )
            self.assertFalse(row.recalled, (category, required, rows))
        self.assertEqual({row.removed_channel for row in rows if row.removed_channel}, set(CHANNELS))


if __name__ == "__main__":
    unittest.main()
