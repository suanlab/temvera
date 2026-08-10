from datetime import datetime, timedelta, timezone
import unittest

from temvera.generator import generate_histories
from temvera.index import (
    ExactIndex,
    HashingVectorIndex,
    LexicalIndex,
    reciprocal_rank_fusion,
    temporal_filter,
)
from temvera.oracle import LifecycleOracle


class LexicalIndexTest(unittest.TestCase):
    def test_rebuild_is_deterministic_and_searches_exact_tokens(self) -> None:
        events = generate_histories(seed=4, entities=2, revisions=2)
        state = LifecycleOracle(events).state_as_of(
            datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        index = LexicalIndex(state.values())
        snapshot = index.snapshot()
        index.rebuild(reversed(tuple(state.values())))
        self.assertEqual(index.snapshot(), snapshot)
        self.assertTrue(index.search("entity-000 location"))
        self.assertTrue(
            all(item.subject == "entity-000" for item in index.search("entity-000"))
        )

    def test_exact_temporal_and_rrf_channels_are_deterministic(self) -> None:
        events = generate_histories(seed=4, entities=1, revisions=3)
        transaction_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        state = LifecycleOracle(events).state_as_of(transaction_at)
        exact = ExactIndex(state.values()).search("ENTITY-000", "LOCATION")
        self.assertEqual(len(exact), 3)
        at = min(item.valid_from for item in exact) + timedelta(days=1)
        historical = temporal_filter(exact, valid_at=at)
        self.assertEqual(len(historical), 1)
        first = reciprocal_rank_fusion(
            {"lexical": ("b2", "b1"), "exact": ("b1", "b2")}
        )
        second = reciprocal_rank_fusion(
            {"exact": ("b1", "b2"), "lexical": ("b2", "b1")}
        )
        self.assertEqual(first, second)
        self.assertEqual([item[0] for item in first], ["b1", "b2"])

    def test_hashing_vector_baseline_is_rebuildable(self) -> None:
        events = generate_histories(seed=6, entities=2, revisions=2)
        state = LifecycleOracle(events).state_as_of(
            datetime(2030, 1, 1, tzinfo=timezone.utc)
        )
        index = HashingVectorIndex(state.values(), dimensions=256)
        snapshot = index.snapshot()
        result = index.search("entity-001 location", limit=2)
        index.rebuild(reversed(tuple(state.values())))
        self.assertEqual(index.snapshot(), snapshot)
        self.assertTrue(result)
        self.assertEqual(index.search("entity-001 location", limit=2), result)


if __name__ == "__main__":
    unittest.main()
