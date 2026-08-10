from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from temvera.generator import generate_histories, generate_lifecycle_suite
from temvera.oracle import LifecycleOracle
from temvera.sqlite_oracle import SqliteBitemporalOracle


class SqliteOracleTest(unittest.TestCase):
    def test_matches_event_replay_across_time_grid(self) -> None:
        events = generate_histories(seed=31, entities=3, revisions=4)
        replay = LifecycleOracle(events)
        sql = SqliteBitemporalOracle()
        self.addCleanup(sql.close)
        sql.extend(events)
        transaction_points = sorted({event.recorded_at for event in events})
        valid_points = sorted(
            {event.valid_from for event in events if event.valid_from is not None}
        )
        for transaction_at in transaction_points:
            self.assertEqual(
                sql.state_as_of(transaction_at), replay.state_as_of(transaction_at)
            )
            for valid_at in valid_points:
                for entity in range(3):
                    key = f"entity-{entity:03d}"
                    self.assertEqual(
                        sql.query(
                            key,
                            "location",
                            valid_at=valid_at,
                            transaction_at=transaction_at,
                        ),
                        replay.query(
                            key,
                            "location",
                            valid_at=valid_at,
                            transaction_at=transaction_at,
                        ),
                    )

    def test_persistent_database_covers_full_lifecycle(self) -> None:
        events = generate_lifecycle_suite(seed=9)
        replay = LifecycleOracle(events)
        with TemporaryDirectory() as directory:
            sql = SqliteBitemporalOracle(Path(directory) / "oracle.sqlite3")
            sql.extend(events)
            after = max(event.recorded_at for event in events) + timedelta(days=1)
            self.assertEqual(sql.state_as_of(after), replay.state_as_of(after))
            sql.close()

    def test_transaction_comparison_normalizes_utc_offsets(self) -> None:
        event = generate_histories(seed=1, entities=1, revisions=1)[0]
        sql = SqliteBitemporalOracle()
        self.addCleanup(sql.close)
        sql.append(event)
        same_instant = event.recorded_at.astimezone(timezone(timedelta(hours=9)))
        self.assertIn(event.belief_id, sql.state_as_of(same_instant))
        just_before = datetime.fromtimestamp(
            event.recorded_at.timestamp() - 1, tz=timezone(timedelta(hours=-5))
        )
        self.assertNotIn(event.belief_id, sql.state_as_of(just_before))


if __name__ == "__main__":
    unittest.main()
