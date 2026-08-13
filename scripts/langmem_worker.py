"""Out-of-process LangMem worker driven over stdio.

LangMem pulls `openai>=3`, which is incompatible with the `openai==1.x` that the
pinned Mem0 and Graphiti versions require. Installing it into the main
environment would invalidate the sealed runs, so it lives in its own virtualenv
and the adapter talks to this worker instead.

Protocol: one JSON object per line on stdin, one per line on stdout.

    {"op": "reset"}                  -> {"ok": true}
    {"op": "ingest", "text": "..."}  -> {"ok": true}
    {"op": "answer", "query": "..."} -> {"ok": true, "answer": "..."}
    {"op": "dump"}                   -> {"ok": true, "memories": [...]}
"""

from __future__ import annotations

import json
import sys


class _Worker:
    def __init__(self, model: str, embed_model: str, limit: int) -> None:
        self._model = model
        self._embed_model = embed_model
        self._limit = limit
        self._namespace = ("memories", "agent")
        self._store = None
        self._manager = None
        self.reset()

    def reset(self) -> None:
        from langgraph.store.memory import InMemoryStore
        from langmem import create_memory_store_manager

        self._store = InMemoryStore(
            index={"dims": 1536, "embed": f"openai:{self._embed_model}"}
        )
        self._manager = create_memory_store_manager(
            f"openai:{self._model}", namespace=self._namespace, store=self._store
        )

    def ingest(self, text: str) -> None:
        self._manager.invoke({"messages": [{"role": "user", "content": text}]})

    def _flatten(self, value) -> str:
        if isinstance(value, dict):
            return " ".join(self._flatten(v) for v in value.values())
        if isinstance(value, (list, tuple)):
            return " ".join(self._flatten(v) for v in value)
        return str(value)

    def answer(self, query: str) -> str:
        hits = self._store.search(self._namespace, query=query, limit=self._limit)
        return " | ".join(self._flatten(hit.value) for hit in hits)

    def dump(self) -> list[str]:
        hits = self._store.search(self._namespace, query="", limit=1000)
        return [self._flatten(hit.value) for hit in hits]


def main() -> int:
    config = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    worker = _Worker(
        config.get("model", "gpt-4o-mini"),
        config.get("embed_model", "text-embedding-3-small"),
        int(config.get("search_limit", 5)),
    )
    print(json.dumps({"ok": True, "ready": True}), flush=True)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            op = request.get("op")
            if op == "reset":
                worker.reset()
                response = {"ok": True}
            elif op == "ingest":
                worker.ingest(request["text"])
                response = {"ok": True}
            elif op == "answer":
                response = {"ok": True, "answer": worker.answer(request["query"])}
            elif op == "dump":
                response = {"ok": True, "memories": worker.dump()}
            elif op == "stop":
                print(json.dumps({"ok": True}), flush=True)
                return 0
            else:
                response = {"ok": False, "error": f"unknown op: {op}"}
        except Exception as error:  # report, never die mid-run
            response = {"ok": False, "error": f"{type(error).__name__}: {error}"}
        print(json.dumps(response), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
