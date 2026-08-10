"""Disposable exact and lexical projections over materialized beliefs."""

from __future__ import annotations

import re
import hashlib
from math import sqrt
from collections import defaultdict
from datetime import datetime
from typing import Iterable, Mapping

from .model import Belief


TOKEN = re.compile(r"[\w-]+", re.UNICODE)
SEMANTIC_ALIASES = {
    "automobile": "car",
    "car": "car",
    "dwelling": "home",
    "home": "home",
    "physician": "doctor",
    "doctor": "doctor",
    "resides": "lives",
    "lives": "lives",
}


def tokenize(text: str) -> frozenset[str]:
    return frozenset(token.casefold() for token in TOKEN.findall(text))


class LexicalIndex:
    def __init__(self, beliefs: Iterable[Belief] = ()) -> None:
        self._beliefs: dict[str, Belief] = {}
        self._postings: dict[str, set[str]] = defaultdict(set)
        self.rebuild(beliefs)

    def rebuild(self, beliefs: Iterable[Belief]) -> None:
        self._beliefs.clear()
        self._postings.clear()
        for belief in sorted(beliefs, key=lambda item: item.belief_id):
            self._beliefs[belief.belief_id] = belief
            text = " ".join((belief.subject, belief.attribute, belief.value))
            for token in tokenize(text):
                self._postings[token].add(belief.belief_id)

    def search(self, query: str, limit: int = 10) -> tuple[Belief, ...]:
        query_tokens = tokenize(query)
        scores: dict[str, int] = defaultdict(int)
        for token in query_tokens:
            for belief_id in self._postings.get(token, ()):
                scores[belief_id] += 1
        ranked = sorted(scores, key=lambda belief_id: (-scores[belief_id], belief_id))
        return tuple(self._beliefs[belief_id] for belief_id in ranked[:limit])

    def snapshot(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple(
            (token, tuple(sorted(ids)))
            for token, ids in sorted(self._postings.items())
        )


class ExactIndex:
    def __init__(self, beliefs: Iterable[Belief]) -> None:
        self._by_key: dict[tuple[str, str], list[Belief]] = defaultdict(list)
        for belief in beliefs:
            self._by_key[(belief.subject.casefold(), belief.attribute.casefold())].append(
                belief
            )
        for values in self._by_key.values():
            values.sort(key=lambda belief: belief.belief_id)

    def search(self, subject: str, attribute: str) -> tuple[Belief, ...]:
        return tuple(self._by_key.get((subject.casefold(), attribute.casefold()), ()))


def temporal_filter(
    beliefs: Iterable[Belief], *, valid_at: datetime
) -> tuple[Belief, ...]:
    return tuple(
        sorted(
            (belief for belief in beliefs if belief.valid_at(valid_at)),
            key=lambda belief: belief.belief_id,
        )
    )


def reciprocal_rank_fusion(
    rankings: Mapping[str, tuple[str, ...]], *, rank_constant: int = 60
) -> tuple[tuple[str, float], ...]:
    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")
    scores: dict[str, float] = defaultdict(float)
    for channel in sorted(rankings):
        for rank, belief_id in enumerate(rankings[channel], start=1):
            scores[belief_id] += 1 / (rank_constant + rank)
    return tuple(sorted(scores.items(), key=lambda item: (-item[1], item[0])))


def weighted_reciprocal_rank_fusion(
    rankings: Mapping[str, tuple[str, ...]],
    weights: Mapping[str, float],
    *,
    rank_constant: int = 60,
) -> tuple[tuple[str, float], ...]:
    if rank_constant <= 0:
        raise ValueError("rank_constant must be positive")
    if any(weight < 0 for weight in weights.values()):
        raise ValueError("fusion weights must be non-negative")
    scores: dict[str, float] = defaultdict(float)
    for channel in sorted(rankings):
        weight = weights.get(channel, 0.0)
        for rank, belief_id in enumerate(rankings[channel], start=1):
            scores[belief_id] += weight / (rank_constant + rank)
    return tuple(
        sorted(
            ((belief_id, score) for belief_id, score in scores.items() if score > 0),
            key=lambda item: (-item[1], item[0]),
        )
    )


class HashingVectorIndex:
    """Dependency-free hashed bag-of-words cosine baseline.

    This is intentionally weak and deterministic. It establishes the local
    dense-channel plumbing before evaluating learned embedding services.
    """

    def __init__(self, beliefs: Iterable[Belief] = (), dimensions: int = 1024) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self.dimensions = dimensions
        self._beliefs: dict[str, Belief] = {}
        self._vectors: dict[str, tuple[float, ...]] = {}
        self.rebuild(beliefs)

    def rebuild(self, beliefs: Iterable[Belief]) -> None:
        self._beliefs.clear()
        self._vectors.clear()
        for belief in sorted(beliefs, key=lambda item: item.belief_id):
            text = " ".join((belief.subject, belief.attribute, belief.value))
            self._beliefs[belief.belief_id] = belief
            self._vectors[belief.belief_id] = self._embed(text)

    def search(self, query: str, limit: int = 10) -> tuple[Belief, ...]:
        query_vector = self._embed(query)
        scores = {
            belief_id: sum(
                    left * right
                    for left, right in zip(query_vector, self._vectors[belief_id])
                )
            for belief_id in self._vectors
        }
        scored = sorted(
            (belief_id for belief_id, score in scores.items() if score > 0),
            key=lambda belief_id: (-scores[belief_id], belief_id),
        )
        return tuple(self._beliefs[belief_id] for belief_id in scored[:limit])

    def snapshot(self) -> dict[str, object]:
        return {
            "dimensions": self.dimensions,
            "vectors": {
                belief_id: list(vector)
                for belief_id, vector in sorted(self._vectors.items())
            },
        }

    def _embed(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        for token in tokenize(text):
            if any(character.isdigit() for character in token):
                continue
            token = SEMANTIC_ALIASES.get(token, token)
            digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            index = number % self.dimensions
            sign = 1.0 if number & 1 else -1.0
            vector[index] += sign
        norm = sqrt(sum(value * value for value in vector))
        if norm:
            vector = [value / norm for value in vector]
        return tuple(vector)


class GraphIndex:
    """Undirected provenance/supersession neighborhood projection."""

    def __init__(self, beliefs: Iterable[Belief] = ()) -> None:
        self._beliefs: dict[str, Belief] = {}
        self._neighbors: dict[str, set[str]] = defaultdict(set)
        self.rebuild(beliefs)

    def rebuild(self, beliefs: Iterable[Belief]) -> None:
        values = tuple(beliefs)
        self._beliefs = {belief.belief_id: belief for belief in values}
        self._neighbors.clear()
        for belief in values:
            linked = (*belief.derived_from, belief.superseded_by)
            for neighbor in linked:
                if neighbor and neighbor in self._beliefs:
                    self._neighbors[belief.belief_id].add(neighbor)
                    self._neighbors[neighbor].add(belief.belief_id)

    def expand(self, seeds: Iterable[str], depth: int = 1) -> tuple[Belief, ...]:
        if depth < 0:
            raise ValueError("depth must be non-negative")
        visited = {seed for seed in seeds if seed in self._beliefs}
        frontier = set(visited)
        for _ in range(depth):
            frontier = {
                neighbor
                for belief_id in frontier
                for neighbor in self._neighbors.get(belief_id, ())
                if neighbor not in visited
            }
            visited.update(frontier)
        return tuple(self._beliefs[key] for key in sorted(visited))

    def snapshot(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        return tuple(
            (belief_id, tuple(sorted(self._neighbors.get(belief_id, ()))))
            for belief_id in sorted(self._beliefs)
        )
