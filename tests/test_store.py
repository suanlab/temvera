from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from temvera.generator import generate_histories
from temvera.oracle import LifecycleOracle
from temvera.store import GitTransactionAdapter, JsonlEventStore


class StoreTest(unittest.TestCase):
    def test_round_trip_and_rebuild_are_byte_deterministic(self) -> None:
        events = generate_histories(seed=42, entities=2, revisions=2)
        with TemporaryDirectory() as directory:
            store = JsonlEventStore(Path(directory))
            store.extend(events)
            self.assertEqual(store.load(), events)
            self.assertTrue(
                store.verify_rebuild(datetime(2030, 1, 1, tzinfo=timezone.utc))
            )
            self.assertEqual(len(list(store.projection_dir.glob("*.md"))), 4)

    def test_duplicate_event_is_rejected_without_mutating_ledger(self) -> None:
        event = generate_histories(seed=1, entities=1, revisions=1)[0]
        with TemporaryDirectory() as directory:
            store = JsonlEventStore(Path(directory))
            store.append(event)
            before = store.ledger_path.read_bytes()
            with self.assertRaises(ValueError):
                store.append(event)
            self.assertEqual(store.ledger_path.read_bytes(), before)

    def test_purge_projection_does_not_claim_raw_ledger_erasure(self) -> None:
        from temvera.generator import generate_lifecycle_suite

        events = generate_lifecycle_suite(seed=5)
        with TemporaryDirectory() as directory:
            store = JsonlEventStore(Path(directory))
            store.extend(events)
            store.rebuild(datetime(2025, 1, 22, tzinfo=timezone.utc))
            self.assertEqual(store.residual_occurrences("redact-me"), ("events.jsonl",))

    def test_redaction_erases_current_payload_and_preserves_receipt(self) -> None:
        from temvera.generator import generate_lifecycle_suite

        events = generate_lifecycle_suite(seed=5)
        with TemporaryDirectory() as directory:
            store = JsonlEventStore(Path(directory))
            store.extend(events)
            receipts = store.redact_payloads(
                {"sensitive", "derived"},
                redacted_at=datetime(2025, 1, 23, tzinfo=timezone.utc),
            )
            self.assertEqual(set(receipts), {"sensitive", "derived"})
            self.assertEqual(store.residual_occurrences("redact-me"), ())
            self.assertEqual(store.residual_occurrences("derived-secret"), ())
            receipt_text = (store.root / "deletion-receipts.jsonl").read_text()
            self.assertNotIn("redact-me", receipt_text)
            self.assertIn(receipts["sensitive"], receipt_text)
            state = LifecycleOracle(store.load()).state_as_of(
                datetime(2025, 1, 19, tzinfo=timezone.utc)
            )
            self.assertEqual(state["sensitive"].value, "[PURGED]")

    def test_redaction_is_all_or_nothing_for_missing_ids(self) -> None:
        event = generate_histories(seed=1, entities=1, revisions=1)[0]
        with TemporaryDirectory() as directory:
            store = JsonlEventStore(Path(directory))
            store.append(event)
            before = store.ledger_path.read_bytes()
            with self.assertRaises(ValueError):
                store.redact_payloads(
                    {event.belief_id, "missing"},
                    redacted_at=event.recorded_at + timedelta(days=1),
                )
            self.assertEqual(store.ledger_path.read_bytes(), before)

    def test_redaction_recovers_receipt_after_post_replace_failure(self) -> None:
        class FailingReceiptStore(JsonlEventStore):
            def _append_redaction_receipts(self, rows):
                raise OSError("injected receipt failure")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            event = generate_histories(seed=13, entities=1, revisions=1)[0]
            failing = FailingReceiptStore(root)
            failing.append(event)
            with self.assertRaisesRegex(OSError, "injected"):
                failing.redact_payloads(
                    {event.belief_id}, redacted_at=event.recorded_at + timedelta(days=1)
                )
            self.assertTrue((root / ".redaction-journal.json").exists())
            self.assertNotIn(event.value, (root / "events.jsonl").read_text())

            recovered = JsonlEventStore(root)
            self.assertTrue(recovered.recover_redactions())
            self.assertFalse((root / ".redaction-journal.json").exists())
            receipts = (root / "deletion-receipts.jsonl").read_text()
            self.assertIn(event.belief_id, receipts)
            self.assertFalse(recovered.recover_redactions())

    def test_git_adapter_commits_named_projection_only(self) -> None:
        with TemporaryDirectory() as directory:
            repository = Path(directory)
            subprocess.run(("git", "init", "-q"), cwd=repository, check=True)
            subprocess.run(
                ("git", "config", "user.email", "test@example.invalid"),
                cwd=repository,
                check=True,
            )
            subprocess.run(
                ("git", "config", "user.name", "Temvera Test"),
                cwd=repository,
                check=True,
            )
            projection = repository / "belief.md"
            unrelated = repository / "private.txt"
            projection.write_text("safe projection\n", encoding="utf-8")
            unrelated.write_text("not committed\n", encoding="utf-8")
            revision = GitTransactionAdapter(repository).commit(
                (projection,), "test projection"
            )
            tracked = subprocess.run(
                ("git", "ls-tree", "--name-only", revision),
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
            self.assertEqual(tracked, ["belief.md"])


if __name__ == "__main__":
    unittest.main()
