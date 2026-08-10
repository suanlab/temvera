"""Rebuildable local event ledger and human-readable projections."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .index import GraphIndex, HashingVectorIndex, LexicalIndex
from .model import Belief, MemoryEvent
from .oracle import LifecycleOracle


class JsonlEventStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.ledger_path = root / "events.jsonl"
        self.projection_dir = root / "beliefs"

    def append(self, event: MemoryEvent) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        known_ids = {existing.event_id for existing in self.load()}
        if event.event_id in known_ids:
            raise ValueError(f"duplicate event_id: {event.event_id}")
        payload = json.dumps(
            event.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        with self.ledger_path.open("a", encoding="utf-8") as stream:
            stream.write(payload + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def extend(self, events: Iterable[MemoryEvent]) -> None:
        for event in events:
            self.append(event)

    def load(self) -> tuple[MemoryEvent, ...]:
        if not self.ledger_path.exists():
            return ()
        events = []
        with self.ledger_path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                try:
                    events.append(MemoryEvent.from_dict(json.loads(line)))
                except (TypeError, ValueError, json.JSONDecodeError) as error:
                    raise ValueError(
                        f"invalid ledger line {line_number}: {self.ledger_path}"
                    ) from error
        return tuple(events)

    def rebuild(self, transaction_at: datetime) -> dict[str, str]:
        oracle = LifecycleOracle(self.load())
        state = oracle.state_as_of(transaction_at)
        self.projection_dir.mkdir(parents=True, exist_ok=True)
        expected = {f"{belief_id}.md" for belief_id in state}
        for path in self.projection_dir.glob("*.md"):
            if path.name not in expected:
                path.unlink()
        checksums: dict[str, str] = {}
        for belief_id, belief in sorted(state.items()):
            content = render_belief(belief)
            path = self.projection_dir / f"{belief_id}.md"
            path.write_text(content, encoding="utf-8")
            checksums[belief_id] = hashlib.sha256(content.encode()).hexdigest()
        manifest = json.dumps(checksums, indent=2, sort_keys=True) + "\n"
        (self.root / "projection-manifest.json").write_text(manifest, encoding="utf-8")
        lexical = LexicalIndex(state.values()).snapshot()
        (self.root / "lexical-index.json").write_text(
            json.dumps(lexical, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        vector = HashingVectorIndex(state.values()).snapshot()
        (self.root / "vector-index.json").write_text(
            json.dumps(vector, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        graph = GraphIndex(state.values()).snapshot()
        (self.root / "graph-index.json").write_text(
            json.dumps(graph, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return checksums

    def verify_rebuild(self, transaction_at: datetime) -> bool:
        first = self.rebuild(transaction_at)
        first_bytes = self._projection_bytes()
        second = self.rebuild(transaction_at)
        second_bytes = self._projection_bytes()
        return first == second and first_bytes == second_bytes

    def _projection_bytes(self) -> dict[str, bytes]:
        paths = (
            *sorted(self.projection_dir.glob("*.md")),
            self.root / "projection-manifest.json",
            self.root / "lexical-index.json",
            self.root / "vector-index.json",
            self.root / "graph-index.json",
        )
        return {
            str(path.relative_to(self.root)): path.read_bytes()
            for path in paths
            if path.exists()
        }

    def redact_payloads(
        self, belief_ids: set[str], *, redacted_at: datetime
    ) -> dict[str, str]:
        """Redact current-ledger payloads with crash-recoverable hash receipts.

        This erases payloads in the current working tree. It cannot erase copies
        already committed to Git or external backups; callers must check those
        stores independently.
        """
        if not belief_ids:
            return {}
        if not self.ledger_path.exists():
            raise ValueError("ledger does not exist")
        journal_path = self.root / ".redaction-journal.json"
        if journal_path.exists():
            raise RuntimeError("unfinished redaction exists; recover it first")
        lines = self.ledger_path.read_text(encoding="utf-8").splitlines()
        rewritten: list[str] = []
        receipts: dict[str, str] = {}
        event_ids: dict[str, list[str]] = {belief_id: [] for belief_id in belief_ids}
        found: set[str] = set()
        for line in lines:
            data = json.loads(line)
            belief_id = data.get("belief_id")
            if belief_id in belief_ids and data.get("operation") == "ingest":
                found.add(belief_id)
                event_ids[belief_id].append(data["event_id"])
                digest = hashlib.sha256(line.encode()).hexdigest()
                receipts[belief_id] = digest
                data.update(
                    subject="[PURGED]",
                    attribute="[PURGED]",
                    value="[PURGED]",
                    sources=[],
                )
                line = json.dumps(
                    data,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            rewritten.append(line)
        missing = belief_ids - found
        if missing:
            raise ValueError(f"beliefs have no ingest payload: {sorted(missing)}")
        receipt_rows = [
            {
                "belief_id": belief_id,
                "event_ids": event_ids[belief_id],
                "original_sha256": receipts[belief_id],
                "redacted_at": redacted_at.isoformat(),
            }
            for belief_id in sorted(receipts)
        ]
        self._write_redaction_journal(journal_path, "prepared", receipt_rows)
        temporary = self.root / ".events.jsonl.redacting"
        with temporary.open("w", encoding="utf-8") as stream:
            stream.write("\n".join(rewritten) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, self.ledger_path)
        self._write_redaction_journal(journal_path, "applied", receipt_rows)
        self._append_redaction_receipts(receipt_rows)
        journal_path.unlink()
        return receipts

    def recover_redactions(self) -> bool:
        """Finish a redaction interrupted after its durable journal was written."""
        journal_path = self.root / ".redaction-journal.json"
        if not journal_path.exists():
            return False
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
        rows = journal["receipts"]
        target_ids = {row["belief_id"] for row in rows}
        ingest_values = {
            data["belief_id"]: data.get("value")
            for data in (
                json.loads(line)
                for line in self.ledger_path.read_text(encoding="utf-8").splitlines()
            )
            if data.get("operation") == "ingest" and data.get("belief_id") in target_ids
        }
        applied = target_ids and all(ingest_values.get(key) == "[PURGED]" for key in target_ids)
        if applied:
            self._append_redaction_receipts(rows)
        journal_path.unlink()
        return bool(applied)

    def _write_redaction_journal(
        self, path: Path, state: str, receipts: list[dict[str, object]]
    ) -> None:
        temporary = path.with_suffix(".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump({"state": state, "receipts": receipts}, stream, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)

    def _append_redaction_receipts(self, rows: list[dict[str, object]]) -> None:
        receipt_path = self.root / "deletion-receipts.jsonl"
        existing = {
            (row["belief_id"], row["original_sha256"])
            for row in (
                json.loads(line)
                for line in receipt_path.read_text(encoding="utf-8").splitlines()
            )
        } if receipt_path.exists() else set()
        with receipt_path.open("a", encoding="utf-8") as stream:
            for row in rows:
                key = (row["belief_id"], row["original_sha256"])
                if key not in existing:
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def residual_occurrences(self, text: str) -> tuple[str, ...]:
        """Locate sensitive payload still present in canonical or derived files."""
        hits = []
        paths = (
            self.ledger_path,
            self.root / "deletion-receipts.jsonl",
            self.root / "projection-manifest.json",
            self.root / "lexical-index.json",
            self.root / "vector-index.json",
            self.root / "graph-index.json",
            self.root / ".redaction-journal.json",
            *sorted(self.projection_dir.glob("*.md")),
        )
        for path in paths:
            if path.exists() and text in path.read_text(encoding="utf-8"):
                hits.append(str(path.relative_to(self.root)))
        return tuple(hits)


class GitTransactionAdapter:
    """Commit a rebuilt projection; Git is an audit layer, not canonical state."""

    def __init__(self, repository: Path) -> None:
        self.repository = repository

    def commit(self, paths: Iterable[Path], message: str) -> str:
        relative_paths = [str(path.relative_to(self.repository)) for path in paths]
        if not relative_paths:
            raise ValueError("at least one path is required")
        self._run("add", "--", *relative_paths)
        self._run("commit", "-m", message, "--", *relative_paths)
        return self._run("rev-parse", "HEAD").strip()

    def _run(self, *arguments: str) -> str:
        result = subprocess.run(
            ("git", *arguments),
            cwd=self.repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout


def render_belief(belief: Belief) -> str:
    fields = {
        "id": belief.belief_id,
        "subject": belief.subject,
        "attribute": belief.attribute,
        "value": belief.value,
        "valid_from": belief.valid_from.isoformat(),
        "valid_to": belief.valid_to.isoformat() if belief.valid_to else "null",
        "recorded_at": belief.recorded_at.isoformat(),
        "last_confirmed_at": belief.last_confirmed_at.isoformat(),
        "status": belief.status,
        "authority": belief.authority.value,
        "superseded_by": belief.superseded_by or "null",
    }
    header = "\n".join(f"{key}: {json.dumps(value)}" for key, value in fields.items())
    sources = "\n".join(f"- {source}" for source in belief.sources) or "- none"
    return f"---\n{header}\n---\n\n# {belief.subject}: {belief.attribute}\n\n{belief.value}\n\n## Sources\n\n{sources}\n"
