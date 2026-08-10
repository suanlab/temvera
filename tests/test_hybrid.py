from datetime import datetime, timezone
import unittest

from temvera.generator import generate_histories, generate_lifecycle_suite
from temvera.hybrid import CHANNELS, HybridRetriever, channel_ablation
from temvera.index import GraphIndex
from temvera.oracle import LifecycleOracle


class HybridTest(unittest.TestCase):
    def test_graph_preserves_provenance_and_supersession_links(self) -> None:
        state = LifecycleOracle(generate_lifecycle_suite(seed=1)).state_as_of(
            datetime(2025, 1, 19, tzinfo=timezone.utc)
        )
        graph = GraphIndex(state.values())
        expanded = {item.belief_id for item in graph.expand(("sensitive",), depth=1)}
        self.assertEqual(expanded, {"sensitive", "derived"})

    def test_all_channel_removal_ablations_run_under_same_limit(self) -> None:
        events = generate_histories(seed=12, entities=3, revisions=3)
        transaction_at = datetime(2030, 1, 1, tzinfo=timezone.utc)
        oracle = LifecycleOracle(events)
        state = tuple(oracle.state_as_of(transaction_at).values())
        cases = []
        for entity in range(3):
            subject = f"entity-{entity:03d}"
            relevant = [belief for belief in state if belief.subject == subject]
            for belief in relevant:
                expected = oracle.query(
                    subject,
                    "location",
                    valid_at=belief.valid_from,
                    transaction_at=transaction_at,
                )
                cases.append(
                    (
                        subject,
                        "location",
                        belief.valid_from,
                        frozenset(item.belief_id for item in expected),
                    )
                )
        rows = channel_ablation(HybridRetriever(state), tuple(cases), limit=5)
        self.assertEqual(len(rows), len(CHANNELS) + 1)
        self.assertEqual(rows[0].channels, CHANNELS)
        self.assertTrue(all(row.cases == len(cases) for row in rows))


if __name__ == "__main__":
    unittest.main()
