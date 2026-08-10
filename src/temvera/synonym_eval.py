"""Learned vs dependency-free dense retrieval on unseen synonyms (E4).

The dependency-free :class:`~temvera.index.HashingVectorIndex` only resolves
synonyms through a small hardcoded ``SEMANTIC_ALIASES`` table, so it generalizes
only to the exact pairs that table was written for. This module measures the
gap a learned embedding model closes by evaluating both channels on paraphrase
queries whose terms are deliberately *absent* from that alias table.

The learned side needs the optional ``[learned]`` extra and a one-time model
download (authorized by D-011); the hashing side is fully deterministic and
offline. See ``docs/paper-plan-systems.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .index import HashingVectorIndex
from .model import Authority, Belief

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

# (stored value, paraphrase query). Neither term appears in
# temvera.index.SEMANTIC_ALIASES, so the hashing channel cannot bridge them.
SYNONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("bicycle", "bike"),
    ("ocean", "sea"),
    ("attorney", "lawyer"),
    ("sofa", "couch"),
    ("elevator", "lift"),
    ("autumn", "fall"),
    ("infant", "baby"),
    ("jail", "prison"),
    ("glad", "happy"),
    ("purchase", "buy"),
)


@dataclass(frozen=True, slots=True)
class VectorChannelComparison:
    model: str
    queries: int
    hashing_recall_at_1: float
    learned_recall_at_1: float


def synonym_retrieval_fixture() -> tuple[
    tuple[Belief, ...], tuple[tuple[str, frozenset[str]], ...]
]:
    """A shared belief pool plus one paraphrase query per synonym pair."""
    beliefs: list[Belief] = []
    cases: list[tuple[str, frozenset[str]]] = []
    for index, (value, query) in enumerate(SYNONYM_PAIRS):
        belief_id = f"syn-{index:02d}"
        beliefs.append(
            Belief(
                belief_id=belief_id,
                subject="topic",
                attribute="note",
                value=value,
                valid_from=_NOW - timedelta(days=30),
                valid_to=None,
                recorded_at=_NOW - timedelta(days=30),
                last_confirmed_at=_NOW - timedelta(days=30),
                authority=Authority.VERIFIED_TOOL,
                sources=(f"fixture:{belief_id}",),
                derived_from=(),
                superseded_by=None,
            )
        )
        cases.append((query, frozenset({belief_id})))
    return tuple(beliefs), tuple(cases)


def _recall_at_1(index, cases: tuple[tuple[str, frozenset[str]], ...]) -> float:
    if not cases:
        raise ValueError("at least one case is required")
    hits = 0
    for query, expected in cases:
        returned = index.search(query, limit=1)
        hits += bool({belief.belief_id for belief in returned} & expected)
    return hits / len(cases)


def hashing_recall(cases=None, beliefs=None) -> float:
    """Offline recall@1 of the dependency-free hashing channel."""
    if beliefs is None or cases is None:
        beliefs, cases = synonym_retrieval_fixture()
    return _recall_at_1(HashingVectorIndex(beliefs), cases)


def compare_vector_channels(
    *, model_name: str = "BAAI/bge-small-en-v1.5"
) -> VectorChannelComparison:
    """Compare hashing vs learned dense retrieval on unseen synonyms."""
    from .learned import FastEmbedVectorIndex

    beliefs, cases = synonym_retrieval_fixture()
    hashing = _recall_at_1(HashingVectorIndex(beliefs), cases)
    learned = _recall_at_1(FastEmbedVectorIndex(beliefs, model_name=model_name), cases)
    return VectorChannelComparison(
        model=model_name,
        queries=len(cases),
        hashing_recall_at_1=hashing,
        learned_recall_at_1=learned,
    )
