"""Dependency-free adapter for the public ForgetEval operation contract."""

from __future__ import annotations

from dataclasses import dataclass

from .index import tokenize


@dataclass(slots=True)
class _TextMemory:
    memory_id: int
    text: str
    active: bool = True


class ForgetEvalAdapter:
    """Expose Temvera's local mutation semantics through ForgetEval's protocol.

    This adapter intentionally uses a deterministic lexical matcher. It is a
    compatibility baseline, not a claim about semantic retrieval quality.
    """

    name = "temvera-lexical"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._next_id = 1
        self._memories: list[_TextMemory] = []

    def inscribe(self, text: str) -> int:
        if not text.strip():
            raise ValueError("text must be non-empty")
        memory_id = self._next_id
        self._next_id += 1
        self._memories.append(_TextMemory(memory_id, text))
        return memory_id

    def recall_texts(self, query: str, k: int = 5) -> list[str]:
        if k < 0:
            raise ValueError("k must be non-negative")
        ranked = self._rank(query)
        return [memory.text for score, memory in ranked[:k] if score > 0]

    def supersede(self, old_query: str, new_text: str) -> None:
        matches = self._rank(old_query)
        if matches and matches[0][0] > 0:
            matches[0][1].active = False
        self.inscribe(new_text)

    def release(self, query: str) -> int:
        return self._deactivate_best(query)

    def purge(self, query: str) -> int:
        return self._deactivate_best(query)

    def _deactivate_best(self, query: str) -> int:
        matches = self._rank(query)
        if not matches or matches[0][0] <= 0:
            return 0
        best_score = matches[0][0]
        selected = [memory for score, memory in matches if score == best_score]
        for memory in selected:
            memory.active = False
        return len(selected)

    def _rank(self, query: str) -> list[tuple[float, _TextMemory]]:
        query_tokens = tokenize(query)
        ranked: list[tuple[float, _TextMemory]] = []
        for memory in self._memories:
            if not memory.active:
                continue
            text_tokens = tokenize(memory.text)
            overlap = len(query_tokens & text_tokens)
            containment = 1.0 if query.casefold() in memory.text.casefold() else 0.0
            score = overlap + containment
            ranked.append((score, memory))
        ranked.sort(key=lambda item: (-item[0], item[1].memory_id))
        return ranked
