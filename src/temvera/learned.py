"""Optional learned dense-retrieval baseline with explicit model metadata."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .model import Belief


@dataclass(frozen=True, slots=True)
class LearnedVectorResult:
    model: str
    queries: int
    recall_at_1: float


class FastEmbedVectorIndex:
    def __init__(
        self,
        beliefs: Iterable[Belief],
        *,
        model_name: str = "BAAI/bge-small-en-v1.5",
    ) -> None:
        from fastembed import TextEmbedding

        self.model_name = model_name
        self._beliefs = tuple(sorted(beliefs, key=lambda item: item.belief_id))
        self._model = TextEmbedding(model_name=model_name)
        texts = [
            " ".join((belief.subject, belief.attribute, belief.value))
            for belief in self._beliefs
        ]
        matrix = np.asarray(list(self._model.embed(texts)), dtype=np.float32)
        self._matrix = _normalize(matrix)

    def search(self, query: str, limit: int = 10) -> tuple[Belief, ...]:
        query_vector = np.asarray(list(self._model.query_embed(query)), dtype=np.float32)
        query_vector = _normalize(query_vector)[0]
        scores = self._matrix @ query_vector
        order = sorted(
            range(len(self._beliefs)),
            key=lambda index: (-float(scores[index]), self._beliefs[index].belief_id),
        )
        return tuple(self._beliefs[index] for index in order[:limit])


def evaluate_learned_vector(
    index: FastEmbedVectorIndex,
    cases: tuple[tuple[str, frozenset[str]], ...],
) -> LearnedVectorResult:
    if not cases:
        raise ValueError("at least one case is required")
    recalled = 0
    for query, expected in cases:
        returned = index.search(query, limit=1)
        recalled += bool({belief.belief_id for belief in returned} & expected)
    return LearnedVectorResult(index.model_name, len(cases), recalled / len(cases))


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms
