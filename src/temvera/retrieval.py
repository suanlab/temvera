"""Evidence-backed packets built from disposable retrieval projections."""

from __future__ import annotations

from dataclasses import dataclass

from .index import LexicalIndex
from .model import Belief


@dataclass(frozen=True, slots=True)
class MemoryPacketItem:
    belief_id: str
    content: str
    source_ids: tuple[str, ...]
    authority: str
    valid_from: str
    valid_to: str | None


@dataclass(frozen=True, slots=True)
class MemoryPacket:
    query: str
    items: tuple[MemoryPacketItem, ...]
    provenance_coverage: float


def build_packet(index: LexicalIndex, query: str, limit: int = 5) -> MemoryPacket:
    beliefs = index.search(query, limit=limit)
    items = tuple(_packet_item(belief) for belief in beliefs)
    covered = sum(bool(item.source_ids) for item in items)
    return MemoryPacket(
        query=query,
        items=items,
        provenance_coverage=covered / len(items) if items else 1.0,
    )


def _packet_item(belief: Belief) -> MemoryPacketItem:
    return MemoryPacketItem(
        belief_id=belief.belief_id,
        content=f"{belief.subject} {belief.attribute}: {belief.value}",
        source_ids=belief.sources,
        authority=belief.authority.value,
        valid_from=belief.valid_from.isoformat(),
        valid_to=belief.valid_to.isoformat() if belief.valid_to else None,
    )
