# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Temvera is a **research project** (not a product) studying temporal, provenance-aware
memory for long-running AI agents: how they store, revise, retrieve, forget, and audit
beliefs. The thesis is that git-native, bitemporal memory can be inspectable, reversible,
and governable while staying competitive on retrieval quality. Correctness and
reproducibility rank above benchmark scores. No production readiness is claimed; claims
outside the frozen synthetic fixtures are explicitly hypotheses.

Read `AGENTS.md` first — it is the binding working agreement. Then `docs/index.md`,
`docs/research-program.md`, and `docs/architecture.md`.

## Commands

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'      # dev extra pulls in pytest, ruff, cryptography

pytest                        # full deterministic suite (addopts = -q)
pytest tests/test_oracle.py   # single file  (note: not every module has a matching test file)
pytest tests/test_store.py::test_name -q   # single test
ruff check .                  # lint (line-length 88, target py311)
```

Requires CPython **3.11+**. Core runtime has **zero dependencies**; `cryptography`
(protected store / crypto-purge tests), `fastembed`+`numpy` (`.[learned]`, optional dense
retrieval), and pytest/ruff are all opt-in extras.

Run `pytest` and `ruff check .` before proposing any release (per `AGENTS.md`).

## The `temvera` CLI

`temvera.cli:main` (argparse) is the single entry point; every subcommand thinly wraps a
function in a `src/temvera/` module. The local baseline needs no model or network:

```bash
temvera generate /tmp/demo --seed 17 --entities 4 --revisions 3   # seeded history
temvera benchmark /tmp/demo        # oracle vs. baselines under identical histories
temvera verify-dataset data/fixtures/lifecycle-v0
temvera verify-artifacts experiments/accepted-runs.json experiments/runs
```

See `REPRODUCING.md` for the full regeneration protocol.

## Architecture (the big picture)

The system is layered so that **raw events are the only source of truth** and everything
else is a rebuildable projection. Understand these boundaries before changing code:

1. **Event ledger — `model.py`, `store.py`.** `MemoryEvent` is a frozen dataclass; the
   history is an append-only sequence of typed `Operation`s (`ingest`, `reconfirm`,
   `supersede`, `expire`, `purge`). `JsonlEventStore` persists it; `GitTransactionAdapter`
   treats git history as the transaction-time ledger. Never mutate past events — revision
   is a new event that supersedes.

2. **Bitemporal oracle — `oracle.py`, `sqlite_oracle.py`.** `LifecycleOracle` folds events
   into `Belief`s and answers point-in-time queries. **Two temporal axes are kept distinct
   everywhere**: `valid_from`/`valid_to` (event/valid time — when a fact is true) vs.
   `recorded_at` (transaction time — when the system learned it). `SqliteBitemporalOracle`
   is an *independent* second implementation used as a cross-check correctness oracle, not
   an operational baseline. All datetimes must be timezone-aware (enforced in
   `MemoryEvent.__post_init__`).

3. **Disposable projections — `index.py`, `hybrid.py`, `retrieval.py`, `learned.py`.**
   Exact/lexical/vector indexes are rebuilt from materialized beliefs and never treated as
   ground truth. Retrieval is **scoped, then multi-channel candidate retrieval, then rank
   fusion (Reciprocal Rank Fusion), then validity/authority/poisoning gates**. Heterogeneous
   raw retriever scores are never compared directly. `build_packet` returns evidence-backed
   `MemoryPacket`s — every returned memory points to supporting sources.

4. **Baselines & evaluation — `evaluation.py`, `decay.py`, `fusion.py`, `efficiency.py`,
   `lifecycle_grid.py`, `hard_cases.py`.** Evaluation is **judge-free/deterministic**:
   the oracle is compared against append-only, full/recent-context, BM25, and
   last-write-wins baselines over the *same* history. `hard_cases.py` exists to avoid
   aggregate metric saturation. Keep development-set tuning (`fusion.py`) separate from
   test evaluation.

5. **Security & governance — `threats.py`, `governance.py`, `security.py`,
   `security_experiment.py`, `protected_store.py`, `bypass.py`.** Untrusted/retrieved text
   is data, never executable policy. Threat fixtures are seeded and non-executable.
   `ProtectedEventStore` separates immutable metadata from per-belief AES-256-GCM-encrypted
   payloads so key destruction yields cryptographic purge (keys live under deny-all-ignored
   `.temvera-keys/`). Note the **purge limitation**: the plain JSONL ledger tombstones but
   does *not* physically erase payloads from `events.jsonl` — tests report residual
   occurrences rather than treating a tombstone as deletion (see `docs/architecture.md`).

6. **Immutable experiment runs — `experiment.py`, `dataset.py`, `artifact.py`.** Runs are
   sealed: they refuse overwrite and embed canonical config, environment, source-tree hash,
   and per-file checksums. Accepted runs are pinned in `experiments/accepted-runs.json` and
   gated by `.gitignore` allowlist entries under `experiments/runs/`.

## Research-integrity workflow (mandatory)

This repo has research controls that ordinary codebases don't. Before changing any research
**claim**:

- Update `docs/evidence-ledger.md` (add/adjust a row); read `docs/research-program.md`.
- Mark anything unsupported as a hypothesis; **preserve negative/contradictory evidence**
  (`docs/negative-results.md`) — do not delete it to make results look cleaner.
- **Never hand-edit raw run outputs** under `experiments/runs/`. Regenerate into a new
  immutable directory instead.
- Pin datasets, seeds, prompts, and environment versions. Add a deterministic test for
  every memory operation or bug fix.
- **Any number the paper prints must have a row in `scripts/verify_paper_claims.py`**,
  declaring both its printed form and how it is recomputed from a sealed run, and
  naming its aggregation (case-weighted vs cell-averaged). `pytest` fails otherwise.
  Prose drifting onto a superseded run is the failure this guards against, and it
  has happened.
- Prefer rebuildable indexes over introducing hidden sources of truth; avoid adding
  external services before a local baseline exists.

## Conventions

- Small, fully typed code (`from __future__ import annotations`, frozen `slots=True`
  dataclasses, `str`-backed enums). Match the existing terse, dependency-free style.
- Determinism is a hard requirement: seed everything, keep outputs canonical
  (`json.dumps(..., sort_keys=True)`), and make async-style operations idempotent.
- CLI output commands write JSON and **refuse to overwrite existing output paths** — keep
  that guard when adding subcommands.
