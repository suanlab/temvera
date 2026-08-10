from datetime import datetime, timedelta, timezone
import unittest

from temvera.decay import (
    DecayCandidate,
    DecayCase,
    confidence_at,
    evaluate_decay,
    rank_only_decay,
    state_level_decay,
)


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class DecayTest(unittest.TestCase):
    def test_half_life_has_exact_interpretation(self) -> None:
        candidate = DecayCandidate("b", 1.0, NOW - timedelta(days=30))
        self.assertAlmostEqual(confidence_at(candidate, NOW, half_life_days=30), 0.5)

    def test_rank_and_state_decay_are_distinct_mechanisms(self) -> None:
        old = DecayCandidate("old", 1.0, NOW - timedelta(days=120))
        fresh = DecayCandidate("fresh", 0.4, NOW)
        self.assertEqual(
            rank_only_decay((old, fresh), at=NOW, half_life_days=30, limit=2),
            ("fresh", "old"),
        )
        self.assertEqual(
            state_level_decay(
                (old, fresh),
                at=NOW,
                half_life_days=30,
                minimum_confidence=0.25,
                limit=2,
            ),
            ("fresh",),
        )

    def test_decay_report_keeps_recall_staleness_and_abstention_separate(self) -> None:
        old = DecayCandidate("stale", 1.0, NOW - timedelta(days=180))
        fresh = DecayCandidate("relevant", 0.8, NOW)
        case = DecayCase((old, fresh), frozenset({"relevant"}), frozenset({"stale"}), NOW)
        result = evaluate_decay((case,), "state_level", half_life_days=30)
        self.assertEqual(result.evidence_recall_at_k, 1.0)
        self.assertEqual(result.stale_use_rate, 0.0)
        self.assertEqual(result.abstention_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
