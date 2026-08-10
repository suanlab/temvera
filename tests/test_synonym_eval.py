import unittest

from temvera.synonym_eval import (
    SYNONYM_PAIRS,
    compare_vector_channels,
    hashing_recall,
    synonym_retrieval_fixture,
)


class SynonymEvalTest(unittest.TestCase):
    def test_fixture_is_one_case_per_pair(self) -> None:
        beliefs, cases = synonym_retrieval_fixture()
        self.assertEqual(len(beliefs), len(SYNONYM_PAIRS))
        self.assertEqual(len(cases), len(SYNONYM_PAIRS))

    def test_hashing_channel_fails_on_unseen_synonyms(self) -> None:
        # The alias table does not cover these pairs, so the hashing baseline
        # cannot bridge query and stored value: recall must be far below 1.
        self.assertLess(hashing_recall(), 0.5)

    def test_learned_channel_beats_hashing(self) -> None:
        try:
            comparison = compare_vector_channels()
        except Exception as error:  # model download / offline / missing extra
            self.skipTest(f"learned model unavailable: {error}")
        self.assertGreater(
            comparison.learned_recall_at_1, comparison.hashing_recall_at_1
        )


if __name__ == "__main__":
    unittest.main()
