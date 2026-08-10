from datetime import datetime, timedelta, timezone
import unittest

from temvera import LifecycleOracle, MemoryEvent, Operation
from temvera.generator import generate_histories, generate_lifecycle_suite


T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


def event(event_id: str, operation: Operation, belief_id: str, **kwargs: object) -> MemoryEvent:
    return MemoryEvent(
        event_id=event_id,
        operation=operation,
        belief_id=belief_id,
        recorded_at=kwargs.pop("recorded_at", T0),
        **kwargs,
    )


class LifecycleOracleTest(unittest.TestCase):
    def test_bitemporal_query_distinguishes_valid_and_transaction_time(self) -> None:
        oracle = LifecycleOracle(
            [
                event(
                    "e1",
                    Operation.INGEST,
                    "b1",
                    subject="alice",
                    attribute="city",
                    value="Seoul",
                    valid_from=T0,
                    recorded_at=T0 + timedelta(days=5),
                )
            ]
        )
        self.assertEqual(
            oracle.query(
                "alice",
                "city",
                valid_at=T0 + timedelta(days=2),
                transaction_at=T0 + timedelta(days=4),
            ),
            (),
        )
        self.assertEqual(
            oracle.query(
                "alice",
                "city",
                valid_at=T0 + timedelta(days=2),
                transaction_at=T0 + timedelta(days=6),
            )[0].value,
            "Seoul",
        )

    def test_supersede_preserves_historical_answer(self) -> None:
        events = [
            event(
                "e1",
                Operation.INGEST,
                "b1",
                subject="alice",
                attribute="city",
                value="Seoul",
                valid_from=T0,
            ),
            event(
                "e2",
                Operation.INGEST,
                "b2",
                subject="alice",
                attribute="city",
                value="Busan",
                valid_from=T0 + timedelta(days=10),
                recorded_at=T0 + timedelta(days=11),
            ),
            event(
                "e3",
                Operation.SUPERSEDE,
                "b2",
                target_id="b1",
                valid_from=T0 + timedelta(days=10),
                recorded_at=T0 + timedelta(days=11),
            ),
        ]
        oracle = LifecycleOracle(events)
        historical = oracle.query(
            "alice",
            "city",
            valid_at=T0 + timedelta(days=5),
            transaction_at=T0 + timedelta(days=20),
        )
        current = oracle.query(
            "alice",
            "city",
            valid_at=T0 + timedelta(days=15),
            transaction_at=T0 + timedelta(days=20),
        )
        self.assertEqual([belief.value for belief in historical], ["Seoul"])
        self.assertEqual([belief.value for belief in current], ["Busan"])

    def test_purge_lineage_is_transitive(self) -> None:
        events = []
        for index, parents in enumerate(((), ("b0",), ("b1",))):
            events.append(
                event(
                    f"e{index}",
                    Operation.INGEST,
                    f"b{index}",
                    subject="s",
                    attribute=f"a{index}",
                    value="v",
                    valid_from=T0,
                    derived_from=parents,
                    sources=("source",),
                )
            )
        self.assertEqual(
            LifecycleOracle(events).purge_lineage("b0", T0), {"b0", "b1", "b2"}
        )

    def test_generator_is_seed_deterministic(self) -> None:
        self.assertEqual(generate_histories(seed=7), generate_histories(seed=7))
        self.assertNotEqual(generate_histories(seed=7), generate_histories(seed=8))

    def test_invalid_ingest_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            event("e", Operation.INGEST, "b", valid_from=T0)

    def test_naive_timestamps_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            MemoryEvent(
                "e",
                Operation.INGEST,
                "b",
                datetime(2025, 1, 1),
                "s",
                "a",
                "v",
                T0,
            )

    def test_full_lifecycle_suite_covers_and_applies_all_operations(self) -> None:
        events = generate_lifecycle_suite(seed=3)
        self.assertEqual({item.operation for item in events}, set(Operation))
        oracle = LifecycleOracle(events)
        before_purge = oracle.state_as_of(T0 + timedelta(days=15))
        after_purge = oracle.state_as_of(T0 + timedelta(days=21))
        self.assertEqual(before_purge["stable"].last_confirmed_at, T0 + timedelta(days=5))
        self.assertEqual(before_purge["temporary"].status, "expired")
        self.assertNotIn("sensitive", after_purge)
        self.assertNotIn("derived", after_purge)


if __name__ == "__main__":
    unittest.main()
