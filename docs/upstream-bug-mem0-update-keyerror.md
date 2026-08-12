# Upstream bug report (draft, not filed)

> Status: **not filed — closed by decision D-012 (2026-08-12).** This document
> is retained as internal evidence for ledger row E-065: the defect biases our
> Mem0 measurements downward, so the numbers we report are conservative. It is
> not a pending action item.

## Title

`UPDATE`/`DELETE` memory actions are silently dropped when the LLM returns an
out-of-range memory id (`KeyError` swallowed by a broad `except`)

## Affected version

`mem0ai==0.1.118`, `mem0/memory/main.py` (sync path around lines 394–472; the
async path repeats the pattern near line 1316). Observed with
`llm=openai/gpt-4o-mini (temperature 0)` and
`embedder=openai/text-embedding-3-small`.

## What happens

Before the update prompt, existing memories are renumbered to positional string
ids and a reverse map is built:

```python
temp_uuid_mapping = {}
for idx, item in enumerate(retrieved_old_memory):
    temp_uuid_mapping[str(idx)] = item["id"]
    retrieved_old_memory[idx]["id"] = str(idx)
```

so the only valid ids are `"0" … "N-1"`. The action handler then dereferences
the LLM-supplied id directly:

```python
elif event_type == "UPDATE":
    self._update_memory(
        memory_id=temp_uuid_mapping[resp.get("id")],
        ...
    )
```

If the model returns an id outside that range — which it does in practice — this
raises `KeyError`, and the surrounding handler catches every exception and only
logs:

```python
except Exception as e:
    logger.error(f"Error processing memory action: {resp}, Error: {e}")
```

The consequence is **silent data loss**: the model correctly decided a stored
memory should be updated (or deleted), the update is discarded, the stale value
remains, and `add()` returns success with no indication that an action failed.
For a memory system this is the failure mode that matters most, because the
retained value is precisely the superseded one.

## Observed frequency

The trigger depends on model output, so it is intermittent. Ingesting 12
LongMemEval `oracle`-split conversations (~24 turns each) produced **7** such
errors (ids `'9'`, `'10'`, `'18'`), and a later 60-conversation run produced
**15** (ids up to `'16'`) — roughly 0.25-0.6 per conversation. Notably, replaying
the single conversation that first produced the error, in isolation, produced
**zero** on one clean run, so a fixed-seed reproduction is not currently
available.

```
Error processing memory action: {'id': '10', 'text': 'Completed 5th project',
 'event': 'UPDATE', 'old_memory': 'Finished 5th project since starting painting classes'},
 Error: '10'
```

Note `'10'` appearing when ids `0..9` exist is consistent with an off-by-one
overrun by the model.

## Minimal reproduction

`scripts/repro_mem0_update_keyerror.py` in this repository drives the public
API with content designed to trigger repeated updates to the same facts. It
prints the number of swallowed action errors captured from the `mem0` logger.

```bash
OPENAI_API_KEY=... python scripts/repro_mem0_update_keyerror.py
```

Because the trigger depends on model output, the script reports counts rather
than asserting a fixed number, and it classifies failures: only a bare
`Error: '<id>'` is counted as this bug, so unrelated failures (for example the
SQLite contention below) are not miscounted as a reproduction. On a clean
isolated replay of instance `06db6396` we observed zero occurrences, while the
larger evaluation runs above showed 7 and 15 - treat the script as a probe, not
a deterministic reproducer.

## Suggested fixes (any of these would remove the silent loss)

1. Validate the id before dereferencing and log a distinct warning:
   `if resp.get("id") not in temp_uuid_mapping: ... continue`.
2. Surface failures to the caller — return the failed actions in `add()`'s
   result, or expose a counter — so callers can detect dropped updates.
3. Narrow the `except Exception` so genuine bugs are not indistinguishable from
   model-format problems.
4. Optionally, re-prompt or fall back to `ADD` when the id is unresolvable, so
   the information is not lost entirely.

## Related: shared history database

Mem0 defaults to one global `~/.mem0/history.db`. Two Mem0 processes running
concurrently produce `attempt to write a readonly database`, which the *same*
broad `except` swallows, again dropping memory actions silently. This corrupted
one of our evaluation runs before we isolated `history_db_path` per run. Both
defects share a root cause: every failure in the action loop is caught, logged
at the same level, and never surfaced to the caller.

## Why we hit it

We compare memory systems on histories with deliberate supersession, so updates
are frequent by construction. The dropped updates bias such an evaluation
against the system, which is why we are reporting it rather than only
documenting it.
