"""Typed lifecycle events shared by the oracle and storage adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class Operation(str, Enum):
    INGEST = "ingest"
    RECONFIRM = "reconfirm"
    SUPERSEDE = "supersede"
    EXPIRE = "expire"
    PURGE = "purge"


class Authority(str, Enum):
    SYSTEM = "system"
    VERIFIED_TOOL = "verified_tool"
    USER = "user"
    EXTERNAL = "external"
    INFERRED = "inferred"


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    event_id: str
    operation: Operation
    belief_id: str
    recorded_at: datetime
    subject: str | None = None
    attribute: str | None = None
    value: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    target_id: str | None = None
    sources: tuple[str, ...] = ()
    derived_from: tuple[str, ...] = ()
    authority: Authority = Authority.EXTERNAL

    def __post_init__(self) -> None:
        if not self.event_id or not self.belief_id:
            raise ValueError("event_id and belief_id must be non-empty")
        if self.operation is Operation.INGEST:
            required = (self.subject, self.attribute, self.value, self.valid_from)
            if any(value is None for value in required):
                raise ValueError("ingest requires subject, attribute, value, valid_from")
        if self.operation is Operation.SUPERSEDE and not self.target_id:
            raise ValueError("supersede requires target_id")
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        for field_name in ("recorded_at", "valid_from", "valid_to"):
            value = getattr(self, field_name)
            if value is not None and value.utcoffset() is None:
                raise ValueError(f"{field_name} must be timezone-aware")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["operation"] = self.operation.value
        result["authority"] = self.authority.value
        for field in ("recorded_at", "valid_from", "valid_to"):
            value = result[field]
            result[field] = value.isoformat() if value else None
        result["sources"] = list(self.sources)
        result["derived_from"] = list(self.derived_from)
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryEvent:
        values = dict(data)
        values["operation"] = Operation(values["operation"])
        values["authority"] = Authority(values.get("authority", "external"))
        for field in ("recorded_at", "valid_from", "valid_to"):
            if values.get(field):
                values[field] = datetime.fromisoformat(values[field])
        values["sources"] = tuple(values.get("sources", ()))
        values["derived_from"] = tuple(values.get("derived_from", ()))
        return cls(**values)


@dataclass(frozen=True, slots=True)
class Belief:
    belief_id: str
    subject: str
    attribute: str
    value: str
    valid_from: datetime
    valid_to: datetime | None
    recorded_at: datetime
    last_confirmed_at: datetime
    authority: Authority
    sources: tuple[str, ...]
    derived_from: tuple[str, ...]
    status: str = "active"
    superseded_by: str | None = None

    def valid_at(self, at: datetime) -> bool:
        return self.valid_from <= at and (self.valid_to is None or at < self.valid_to)
