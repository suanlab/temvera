from datetime import datetime, timezone
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest

from temvera.generator import generate_histories
from temvera.model import Authority, MemoryEvent, Operation
from temvera.protected_store import ProtectedEventStore


NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def secret_event() -> MemoryEvent:
    return MemoryEvent(
        "event-secret",
        Operation.INGEST,
        "belief-secret",
        NOW,
        "patient-alice",
        "diagnosis",
        "sensitive-value-123",
        NOW,
        sources=("private-record",),
        authority=Authority.USER,
    )


class ProtectedStoreTest(unittest.TestCase):
    def test_plaintext_never_enters_ledger_and_round_trip_decrypts(self) -> None:
        with TemporaryDirectory() as directory:
            store = ProtectedEventStore(Path(directory))
            event = secret_event()
            store.append(event)
            ledger = store.ledger_path.read_text(encoding="utf-8")
            self.assertNotIn("sensitive-value-123", ledger)
            self.assertNotIn("patient-alice", ledger)
            self.assertEqual(store.load(), (event,))

    def test_key_destruction_makes_historical_ciphertext_unreadable(self) -> None:
        with TemporaryDirectory() as directory:
            store = ProtectedEventStore(Path(directory))
            store.append(secret_event())
            receipts = store.cryptographic_purge(
                {"belief-secret"}, purged_at=NOW
            )
            self.assertIn("belief-secret", receipts)
            restored = store.load()[0]
            self.assertEqual(restored.value, "[PURGED]")
            self.assertNotIn(
                "sensitive-value-123", store.receipt_path.read_text(encoding="utf-8")
            )

    def test_crypto_purge_recovers_after_receipt_failure(self) -> None:
        class FailingReceiptStore(ProtectedEventStore):
            def _append_crypto_receipts(self, rows):
                raise OSError("injected receipt failure")

        with TemporaryDirectory() as directory:
            root = Path(directory)
            events = generate_histories(seed=22, entities=2, revisions=1)
            ingests = [event for event in events if event.operation is Operation.INGEST]
            failing = FailingReceiptStore(root)
            failing.extend(ingests)
            belief_ids = {event.belief_id for event in ingests}
            with self.assertRaisesRegex(OSError, "injected"):
                failing.cryptographic_purge(belief_ids, purged_at=NOW)
            self.assertTrue((root / ".crypto-purge-journal.json").exists())

            recovered = ProtectedEventStore(root)
            self.assertTrue(recovered.recover_crypto_purge())
            self.assertFalse((root / ".crypto-purge-journal.json").exists())
            self.assertFalse(recovered.recover_crypto_purge())
            self.assertEqual(
                {event.value for event in recovered.load()},
                {"[PURGED]"},
            )
            receipt_lines = recovered.receipt_path.read_text().splitlines()
            self.assertEqual(len(receipt_lines), len(belief_ids))

    def test_git_commit_and_clone_do_not_contain_keys_or_plaintext(self) -> None:
        with TemporaryDirectory() as directory, TemporaryDirectory() as clone_dir:
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
            store = ProtectedEventStore(repository / "memory")
            store.append(secret_event())
            subprocess.run(("git", "add", "memory"), cwd=repository, check=True)
            subprocess.run(
                ("git", "commit", "-qm", "protected memory"),
                cwd=repository,
                check=True,
            )
            tracked = subprocess.run(
                ("git", "ls-files"),
                cwd=repository,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn(".key", tracked)
            self.assertNotIn(
                b"sensitive-value-123",
                subprocess.run(
                    ("git", "show", "HEAD"),
                    cwd=repository,
                    check=True,
                    capture_output=True,
                ).stdout,
            )
            clone = Path(clone_dir) / "clone"
            subprocess.run(
                ("git", "clone", "-q", str(repository), str(clone)), check=True
            )
            clone_store = ProtectedEventStore(clone / "memory")
            self.assertEqual(clone_store.load()[0].value, "[PURGED]")


if __name__ == "__main__":
    unittest.main()
