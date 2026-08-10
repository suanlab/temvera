"""Independent SQLite bitemporal oracle over immutable lifecycle events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .model import Authority, Belief, MemoryEvent


SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL,
    belief_id TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    subject TEXT,
    attribute TEXT,
    value TEXT,
    valid_from TEXT,
    valid_to TEXT,
    target_id TEXT,
    sources TEXT NOT NULL,
    derived_from TEXT NOT NULL,
    authority TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_belief_recorded
ON events(belief_id, recorded_at);
CREATE INDEX IF NOT EXISTS events_target_recorded
ON events(target_id, recorded_at);
"""


class SqliteBitemporalOracle:
    def __init__(self, path: Path | str = ":memory:") -> None:
        self.connection = sqlite3.connect(str(path))
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)

    def close(self) -> None:
        self.connection.close()

    def append(self, event: MemoryEvent) -> None:
        data = event.to_dict()
        try:
            with self.connection:
                self.connection.execute(
                    """INSERT INTO events VALUES (
                    :event_id, :operation, :belief_id, :recorded_at,
                    :subject, :attribute, :value, :valid_from, :valid_to,
                    :target_id, :sources, :derived_from, :authority
                    )""",
                    {
                        **data,
                        "sources": json.dumps(data["sources"], sort_keys=True),
                        "derived_from": json.dumps(
                            data["derived_from"], sort_keys=True
                        ),
                    },
                )
        except sqlite3.IntegrityError as error:
            raise ValueError(f"duplicate event_id: {event.event_id}") from error

    def extend(self, events: Iterable[MemoryEvent]) -> None:
        for event in events:
            self.append(event)

    def state_as_of(self, transaction_at: datetime) -> dict[str, Belief]:
        rows = self.connection.execute(
            """
            SELECT i.*,
              (SELECT r.recorded_at FROM events r
               WHERE r.operation = 'reconfirm' AND r.belief_id = i.belief_id
                 AND julianday(r.recorded_at) <= julianday(:transaction_at)
               ORDER BY julianday(r.recorded_at) DESC, r.event_id DESC
               LIMIT 1) AS reconfirmed_at,
              (SELECT s.valid_from FROM events s
               WHERE s.operation = 'supersede' AND s.target_id = i.belief_id
                 AND julianday(s.recorded_at) <= julianday(:transaction_at)
               ORDER BY julianday(s.valid_from), s.event_id LIMIT 1) AS superseded_at,
              (SELECT e.valid_to FROM events e
               WHERE e.operation = 'expire' AND e.belief_id = i.belief_id
                 AND julianday(e.recorded_at) <= julianday(:transaction_at)
               ORDER BY julianday(e.valid_to), e.event_id LIMIT 1) AS expired_at,
              (SELECT s.belief_id FROM events s
               WHERE s.operation = 'supersede' AND s.target_id = i.belief_id
                 AND julianday(s.recorded_at) <= julianday(:transaction_at)
               ORDER BY julianday(s.valid_from), s.event_id LIMIT 1) AS superseded_by
            FROM events i
            WHERE i.operation = 'ingest'
              AND julianday(i.recorded_at) <= julianday(:transaction_at)
              AND NOT EXISTS (
                SELECT 1 FROM events p WHERE p.operation = 'purge'
                  AND p.belief_id = i.belief_id
                  AND julianday(p.recorded_at) <= julianday(:transaction_at))
            ORDER BY i.belief_id
            """,
            {"transaction_at": transaction_at.isoformat()},
        ).fetchall()
        result: dict[str, Belief] = {}
        for row in rows:
            cutoffs = [
                datetime.fromisoformat(value)
                for value in (row["valid_to"], row["superseded_at"], row["expired_at"])
                if value is not None
            ]
            valid_to = min(cutoffs) if cutoffs else None
            status = "active"
            if row["superseded_at"] is not None and valid_to == datetime.fromisoformat(
                row["superseded_at"]
            ):
                status = "superseded"
            elif row["expired_at"] is not None:
                status = "expired"
            recorded_at = datetime.fromisoformat(row["recorded_at"])
            result[row["belief_id"]] = Belief(
                belief_id=row["belief_id"],
                subject=row["subject"],
                attribute=row["attribute"],
                value=row["value"],
                valid_from=datetime.fromisoformat(row["valid_from"]),
                valid_to=valid_to,
                recorded_at=recorded_at,
                last_confirmed_at=(
                    datetime.fromisoformat(row["reconfirmed_at"])
                    if row["reconfirmed_at"]
                    else recorded_at
                ),
                authority=Authority(row["authority"]),
                sources=tuple(json.loads(row["sources"])),
                derived_from=tuple(json.loads(row["derived_from"])),
                status=status,
                superseded_by=row["superseded_by"],
            )
        return result

    def query(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        transaction_at: datetime,
    ) -> tuple[Belief, ...]:
        return tuple(
            sorted(
                (
                    belief
                    for belief in self.state_as_of(transaction_at).values()
                    if belief.subject == subject
                    and belief.attribute == attribute
                    and belief.valid_at(valid_at)
                ),
                key=lambda belief: (
                    belief.valid_from,
                    belief.recorded_at,
                    belief.belief_id,
                ),
                reverse=True,
            )
        )
