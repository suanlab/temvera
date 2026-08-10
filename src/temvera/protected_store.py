"""Append-only metadata with per-belief encrypted payload separation."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .model import MemoryEvent, Operation


class ProtectedEventStore:
    """Keep secrets out of Git history and erase them by destroying keys.

    Metadata, validity, lineage identifiers, and ciphertext remain auditable.
    Subject, attribute, value, and sources are encrypted with a per-belief key.
    The key directory contains its own deny-all `.gitignore`.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.ledger_path = root / "protected-events.jsonl"
        self.payload_dir = root / "payloads"
        self.key_dir = root / ".temvera-keys"
        self.receipt_path = root / "crypto-deletion-receipts.jsonl"

    def append(self, event: MemoryEvent) -> None:
        self._initialize()
        if any(item.event_id == event.event_id for item in self.load()):
            raise ValueError(f"duplicate event_id: {event.event_id}")
        data = event.to_dict()
        if event.operation is Operation.INGEST:
            key = self._load_or_create_key(event.belief_id)
            payload = {
                "attribute": data["attribute"],
                "sources": data["sources"],
                "subject": data["subject"],
                "value": data["value"],
            }
            ciphertext = self._encrypt(
                key,
                json.dumps(payload, sort_keys=True).encode(),
                event.event_id.encode(),
            )
            payload_path = self.payload_dir / f"{_safe_name(event.event_id)}.bin"
            _exclusive_write(payload_path, ciphertext)
            data.update(
                subject="[ENCRYPTED]",
                attribute="[ENCRYPTED]",
                value="[ENCRYPTED]",
                sources=[],
                payload_ref=str(payload_path.relative_to(self.root)),
                payload_sha256=hashlib.sha256(ciphertext).hexdigest(),
            )
        line = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def extend(self, events: Iterable[MemoryEvent]) -> None:
        for event in events:
            self.append(event)

    def load(self) -> tuple[MemoryEvent, ...]:
        if not self.ledger_path.exists():
            return ()
        result = []
        for line_number, line in enumerate(
            self.ledger_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            data = json.loads(line)
            payload_ref = data.pop("payload_ref", None)
            expected_digest = data.pop("payload_sha256", None)
            if payload_ref:
                payload_path = self.root / payload_ref
                ciphertext = payload_path.read_bytes()
                actual_digest = hashlib.sha256(ciphertext).hexdigest()
                if actual_digest != expected_digest:
                    raise ValueError(f"payload checksum mismatch on line {line_number}")
                key_path = self._key_path(data["belief_id"])
                if key_path.exists():
                    plaintext = self._decrypt(
                        key_path.read_bytes(), ciphertext, data["event_id"].encode()
                    )
                    payload = json.loads(plaintext)
                    data.update(payload)
                else:
                    data.update(
                        subject="[PURGED]",
                        attribute="[PURGED]",
                        value="[PURGED]",
                        sources=[],
                    )
            result.append(MemoryEvent.from_dict(data))
        return tuple(result)

    def cryptographic_purge(
        self, belief_ids: set[str], *, purged_at: datetime
    ) -> dict[str, str]:
        if not belief_ids:
            return {}
        known = {event.belief_id for event in self.load() if event.operation is Operation.INGEST}
        missing = belief_ids - known
        if missing:
            raise ValueError(f"unknown ingest beliefs: {sorted(missing)}")
        receipts: dict[str, str] = {}
        self._initialize()
        journal_path = self.root / ".crypto-purge-journal.json"
        if journal_path.exists():
            raise RuntimeError("unfinished cryptographic purge exists; recover it first")
        for belief_id in sorted(belief_ids):
            key_path = self._key_path(belief_id)
            if not key_path.exists():
                raise ValueError(f"key already absent: {belief_id}")
            key_digest = hashlib.sha256(key_path.read_bytes()).hexdigest()
            receipts[belief_id] = key_digest
        rows = [
            {
                "belief_id": belief_id,
                "destroyed_key_sha256": receipts[belief_id],
                "purged_at": purged_at.isoformat(),
            }
            for belief_id in sorted(receipts)
        ]
        self._write_purge_journal(journal_path, "prepared", rows)
        for belief_id in sorted(belief_ids):
            self._key_path(belief_id).unlink()
        self._write_purge_journal(journal_path, "applied", rows)
        self._append_crypto_receipts(rows)
        journal_path.unlink()
        return receipts

    def recover_crypto_purge(self) -> bool:
        """Finish key destruction and receipts after an interrupted purge."""
        journal_path = self.root / ".crypto-purge-journal.json"
        if not journal_path.exists():
            return False
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        rows = journal["receipts"]
        for row in rows:
            key_path = self._key_path(row["belief_id"])
            if key_path.exists():
                digest = hashlib.sha256(key_path.read_bytes()).hexdigest()
                if digest != row["destroyed_key_sha256"]:
                    raise ValueError(f"key digest changed: {row['belief_id']}")
                key_path.unlink()
        self._append_crypto_receipts(rows)
        journal_path.unlink()
        return True

    def _write_purge_journal(
        self, path: Path, state: str, receipts: list[dict[str, str]]
    ) -> None:
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump({"state": state, "receipts": receipts}, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def _append_crypto_receipts(self, rows: list[dict[str, str]]) -> None:
        existing = {
            (row["belief_id"], row["destroyed_key_sha256"])
            for row in (
                json.loads(line)
                for line in self.receipt_path.read_text(encoding="utf-8").splitlines()
            )
        } if self.receipt_path.exists() else set()
        with self.receipt_path.open("a", encoding="utf-8") as stream:
            for row in rows:
                key = (row["belief_id"], row["destroyed_key_sha256"])
                if key not in existing:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def _initialize(self) -> None:
        self.payload_dir.mkdir(parents=True, exist_ok=True)
        self.key_dir.mkdir(parents=True, exist_ok=True)
        ignore = self.key_dir / ".gitignore"
        if not ignore.exists():
            ignore.write_text("*\n!.gitignore\n", encoding="utf-8")

    def _key_path(self, belief_id: str) -> Path:
        return self.key_dir / f"{_safe_name(belief_id)}.key"

    def _load_or_create_key(self, belief_id: str) -> bytes:
        key_path = self._key_path(belief_id)
        if key_path.exists():
            return key_path.read_bytes()
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = AESGCM.generate_key(bit_length=256)
        _exclusive_write(key_path, key, mode=0o600)
        return key

    @staticmethod
    def _encrypt(key: bytes, plaintext: bytes, aad: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        nonce = os.urandom(12)
        return nonce + AESGCM(key).encrypt(nonce, plaintext, aad)

    @staticmethod
    def _decrypt(key: bytes, ciphertext: bytes, aad: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        return AESGCM(key).decrypt(ciphertext[:12], ciphertext[12:], aad)


def _safe_name(identifier: str) -> str:
    return hashlib.sha256(identifier.encode()).hexdigest()


def _exclusive_write(path: Path, content: bytes, mode: int = 0o644) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
