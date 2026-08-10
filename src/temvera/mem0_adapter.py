"""Text-only Mem0 adapter for the external-comparison harness (E1).

Wraps the Mem0 OSS ``Memory`` store behind the harness ``MemorySystem``
contract so it is scored against the same bitemporal truth as the internal
oracle. Mem0 performs LLM-based extraction and consolidation on ingest, so it
answers from a single current-state view and has no transaction-time ``as-of``
concept — the divergence this experiment measures (E-025).

The ``mem0`` dependency is imported lazily; only the E1 runner needs it. LLM
backbone, embedder, and Mem0 version are recorded in the sealed run config for
reproducibility (D-010).
"""

from __future__ import annotations

from typing import Any

from .nl_workload import NLQueryCase, WorkloadTurn


def default_mem0_config(
    *, model: str = "gpt-4o-mini", embed_model: str = "text-embedding-3-small"
) -> dict[str, Any]:
    return {
        "llm": {
            "provider": "openai",
            "config": {"model": model, "temperature": 0.0},
        },
        "embedder": {
            "provider": "openai",
            "config": {"model": embed_model},
        },
    }


class Mem0System:
    """Mem0 OSS store as a harness-compatible memory system."""

    def __init__(
        self,
        *,
        config: dict[str, Any] | None = None,
        user_id: str = "temvera-e1",
        search_limit: int = 5,
    ) -> None:
        from mem0 import Memory

        self._config = config or default_mem0_config()
        self._user_id = user_id
        self._search_limit = search_limit
        self._memory = Memory.from_config(self._config)
        self.last_added: list[dict[str, Any]] = []

    @property
    def version(self) -> str:
        import mem0

        return getattr(mem0, "__version__", "unknown")

    def reset(self) -> None:
        try:
            self._memory.delete_all(user_id=self._user_id)
        except Exception:
            # A fresh store has nothing to delete; ignore.
            pass

    def ingest(self, turn: WorkloadTurn) -> None:
        self._memory.add(turn.text, user_id=self._user_id)

    def answer(self, case: NLQueryCase) -> str:
        result = self._memory.search(
            case.query_text, user_id=self._user_id, limit=self._search_limit
        )
        rows = result.get("results", result) if isinstance(result, dict) else result
        memories = [
            str(row.get("memory", "")) for row in rows if isinstance(row, dict)
        ]
        return " | ".join(memory for memory in memories if memory)
