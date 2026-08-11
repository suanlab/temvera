"""Minimal reproduction for the Mem0 dropped-UPDATE bug.

See docs/upstream-bug-mem0-update-keyerror.md. Mem0 renumbers existing memories
to positional ids "0".."N-1" before asking the LLM which to update; if the model
answers with an id outside that range, `temp_uuid_mapping[...]` raises KeyError,
which is swallowed by a broad `except` and only logged. The update is lost and
`add()` still reports success.

Run with a working OpenAI key:

    OPENAI_API_KEY=... python scripts/repro_mem0_update_keyerror.py

Exit status is 0 whether or not the bug reproduces (it depends on model output);
the script reports how many memory actions were dropped.
"""

from __future__ import annotations

import logging
import os
import re
import sys
import tempfile


class _ActionErrorCounter(logging.Handler):
    """Split dropped-action logs into this bug versus unrelated failures.

    Mem0 logs every failed memory action through one broad `except`, so a
    SQLite contention error looks identical to the id-mapping KeyError unless
    the message is classified. Counting them together would misreport an
    environment problem as a reproduction.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.ERROR)
        self.keyerror: list[str] = []
        self.other: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        text = record.getMessage()
        if "Error processing memory action" not in text:
            return
        # The KeyError surfaces as `Error: '<id>'` - a bare quoted id.
        if re.search(r"Error: '\d+'\s*$", text):
            self.keyerror.append(text)
        else:
            self.other.append(text)


def longmemeval_turns(path: str, question_id: str) -> list[str]:
    """Turns from the real conversation that surfaced the bug for us.

    LongMemEval instance `06db6396` (knowledge-update) triggered dropped UPDATE
    actions during our evaluation. Pass `--dataset <longmemeval_oracle.json>` to
    replay it; the file is not redistributed with this repository.
    """
    import json

    with open(path, encoding="utf-8") as stream:
        data = json.load(stream)
    instance = next(row for row in data if str(row["question_id"]) == question_id)
    turns: list[str] = []
    for session in instance["haystack_sessions"]:
        for turn in session:
            content = (turn.get("content") or "").strip()
            if content:
                turns.append(f"{turn.get('role', 'user')}: {content}")
    return turns


# Fallback synthetic conversation. It repeatedly revises the same facts, but in
# our runs it did NOT reliably trigger the bug - the real conversation above is
# the dependable reproduction.
TURNS = [
    "I just started painting classes and finished my 1st project.",
    "I live in Seoul and my commute is 40 minutes.",
    "My personal best in the 5K is 27 minutes.",
    "Update: I finished my 3rd painting project this week.",
    "I moved to Busan last month, so my commute is now 15 minutes.",
    "New personal best in the 5K: 25 minutes and 50 seconds.",
    "Correction, it was my 5th painting project, not the 3rd.",
    "I am setting up a small art studio in the spare bedroom.",
    "Actually I am only thinking about the studio, not doing it yet.",
    "My 5K best is now 25:10 after this weekend's race.",
    "I switched from painting to sculpture classes.",
    "My commute changed again, it is 25 minutes now.",
]


def main() -> int:
    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set", file=sys.stderr)
        return 2

    turns = TURNS
    if "--dataset" in sys.argv:
        dataset = sys.argv[sys.argv.index("--dataset") + 1]
        question_id = (
            sys.argv[sys.argv.index("--question-id") + 1]
            if "--question-id" in sys.argv
            else "06db6396"
        )
        turns = longmemeval_turns(dataset, question_id)
        print(f"replaying LongMemEval instance {question_id}: {len(turns)} turns")

    from mem0 import Memory

    counter = _ActionErrorCounter()
    logging.getLogger("mem0").addHandler(counter)
    logging.getLogger("mem0").setLevel(logging.ERROR)

    memory = Memory.from_config(
        {
            "llm": {
                "provider": "openai",
                "config": {"model": "gpt-4o-mini", "temperature": 0.0},
            },
            "embedder": {
                "provider": "openai",
                "config": {"model": "text-embedding-3-small"},
            },
            # Isolate from the global ~/.mem0/history.db so a concurrent Mem0
            # process cannot inject unrelated SQLite errors.
            "history_db_path": os.path.join(
                tempfile.mkdtemp(prefix="mem0-repro-"), "history.db"
            ),
        }
    )
    user_id = "mem0-update-keyerror-repro"
    try:
        memory.delete_all(user_id=user_id)
    except Exception:
        pass

    for turn in turns:
        memory.add(turn, user_id=user_id)

    result = memory.get_all(user_id=user_id)
    rows = result.get("results", result) if isinstance(result, dict) else result

    print(f"turns ingested      : {len(turns)}")
    print(f"memories retained   : {len(rows)}")
    print(f"dropped (id KeyError): {len(counter.keyerror)}")
    print(f"dropped (other cause): {len(counter.other)}")
    for message in counter.keyerror:
        print(f"  - {message}")
    for message in counter.other:
        print(f"  ? unrelated: {message}")
    if counter.keyerror:
        print("\nReproduced: an UPDATE/DELETE was dropped by the id-mapping KeyError.")
    else:
        print("\nNot reproduced in this run (trigger depends on model output).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
