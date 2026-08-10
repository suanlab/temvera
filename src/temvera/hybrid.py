"""Fixed-budget deterministic hybrid retrieval and channel ablations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .index import (
    ExactIndex,
    GraphIndex,
    HashingVectorIndex,
    LexicalIndex,
    reciprocal_rank_fusion,
)
from .model import Belief


CHANNELS = ("exact", "lexical", "vector", "temporal", "graph")


class HybridRetriever:
    def __init__(self, beliefs: tuple[Belief, ...]) -> None:
        self.beliefs = beliefs
        self.exact = ExactIndex(beliefs)
        self.lexical = LexicalIndex(beliefs)
        self.vector = HashingVectorIndex(beliefs)
        self.graph = GraphIndex(beliefs)

    def retrieve(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        query_text: str | None = None,
        channels: tuple[str, ...] = CHANNELS,
        limit: int = 5,
    ) -> tuple[Belief, ...]:
        rankings = self.rankings(
            subject,
            attribute,
            valid_at=valid_at,
            query_text=query_text,
            channels=channels,
            limit=limit,
        )
        fused = reciprocal_rank_fusion(rankings)
        by_id = {belief.belief_id: belief for belief in self.beliefs}
        ordered = (by_id[belief_id] for belief_id, _ in fused)
        if "temporal" in channels:
            ordered = (belief for belief in ordered if belief.valid_at(valid_at))
        return tuple(list(ordered)[:limit])

    def rankings(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        query_text: str | None = None,
        channels: tuple[str, ...] = CHANNELS,
        limit: int = 5,
    ) -> dict[str, tuple[str, ...]]:
        unknown = set(channels) - set(CHANNELS)
        if unknown:
            raise ValueError(f"unknown channels: {sorted(unknown)}")
        query = query_text or f"{subject} {attribute}"
        exact = self.exact.search(subject, attribute)
        rankings: dict[str, tuple[str, ...]] = {}
        if "exact" in channels:
            rankings["exact"] = tuple(item.belief_id for item in exact)
        if "lexical" in channels:
            rankings["lexical"] = tuple(
                item.belief_id for item in self.lexical.search(query, limit=limit * 2)
            )
        if "vector" in channels:
            rankings["vector"] = tuple(
                item.belief_id for item in self.vector.search(query, limit=limit * 2)
            )
        if "graph" in channels:
            graph_seeds = {
                belief_id for ranking in rankings.values() for belief_id in ranking
            }
            rankings["graph"] = tuple(
                item.belief_id
                for item in self.graph.expand(
                    graph_seeds, depth=1
                )
                if item.belief_id not in graph_seeds
            )
        return rankings


@dataclass(frozen=True, slots=True)
class AblationRow:
    channels: tuple[str, ...]
    cases: int
    evidence_recall_at_k: float


@dataclass(frozen=True, slots=True)
class HardRetrievalCase:
    category: str
    subject: str
    attribute: str
    query_text: str
    valid_at: datetime
    expected_ids: frozenset[str]
    limit: int


@dataclass(frozen=True, slots=True)
class HardAblationRow:
    category: str
    removed_channel: str | None
    recalled: bool


def hard_channel_ablation(
    retriever: HybridRetriever, cases: tuple[HardRetrievalCase, ...]
) -> tuple[HardAblationRow, ...]:
    rows = []
    for case in cases:
        for removed in (None, *CHANNELS):
            channels = tuple(
                channel for channel in CHANNELS if channel != removed
            )
            returned = retriever.retrieve(
                case.subject,
                case.attribute,
                valid_at=case.valid_at,
                query_text=case.query_text,
                channels=channels,
                limit=case.limit,
            )
            returned_ids = {belief.belief_id for belief in returned}
            rows.append(
                HardAblationRow(
                    category=case.category,
                    removed_channel=removed,
                    recalled=bool(returned_ids & case.expected_ids),
                )
            )
    return tuple(rows)


def channel_ablation(
    retriever: HybridRetriever,
    cases: tuple[tuple[str, str, datetime, frozenset[str]], ...],
    *,
    limit: int = 5,
) -> tuple[AblationRow, ...]:
    rows = []
    configurations = (CHANNELS,) + tuple(
        tuple(channel for channel in CHANNELS if channel != removed)
        for removed in CHANNELS
    )
    for channels in configurations:
        recall = 0.0
        for subject, attribute, valid_at, expected in cases:
            returned = retriever.retrieve(
                subject,
                attribute,
                valid_at=valid_at,
                channels=channels,
                limit=limit,
            )
            returned_ids = {belief.belief_id for belief in returned}
            recall += len(returned_ids & expected) / len(expected) if expected else 1.0
        rows.append(AblationRow(channels, len(cases), recall / len(cases)))
    return tuple(rows)
