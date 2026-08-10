# Auditable Bitemporal Memory for Long-Running Agents

> Systems-paper working draft. Structure follows
> [paper-plan-systems.md](./paper-plan-systems.md) §5. Every result sentence
> carries an evidence-ledger ID; sections gated on external-system runs (E1)
> and external-validity data (E2/E7) are marked **PENDING (D-010)** and must not
> be written as completed until those runs exist.

## Abstract

Persistent agent memory must distinguish when a fact was valid from when the
system learned it, and must preserve revision and deletion semantics across
derived stores. We present a typed, append-only research substrate with an
independent SQLite bitemporal oracle, deterministic rebuilds, purge lineage,
and provenance-aware action gating. The contribution is not Git storage,
temporal fields, confidence decay, or judge-free forgetting in isolation;
Springdrift, Graphiti, Hindsight, Mem0, and ForgetEval already cover adjacent
capabilities (E-005, E-009, E-024, E-025, E-032). Instead we contribute an
independently *verifiable* account of temporal correctness and deletion/audit
semantics, measured against deployed systems under identical budgets.

Across a synthetic 3-profile lifecycle grid (10 seeds), the oracle preserved
exact state in every condition while raw-context, recency, BM25, and
last-write-wins baselines exposed distinct stale-state failures that worsen with
churn (E-044, E-049). A learned dense channel resolved held-out synonyms that
the dependency-free hashing channel could not (E-050). Under identical histories,
two deployed systems diverge from the oracle in distinct ways — Mem0 forgets
historical valid-time (exact 0.607) and Graphiti retains edges but does not
temporally filter them (exact 0.224), while both fail expiry and purge (E-053,
E-054). The result establishes mechanism identifiability, a verifiable substrate,
and measured external divergence — not superiority on natural conversations.

## 1. Introduction

Long-running agents accumulate facts that change, expire, get corrected, and
must sometimes be deleted. Two questions any such memory must answer are *what
was true at time t* (valid time) and *what did the agent know at time t*
(transaction time); current-state stores conflate them. We ask whether a
file/Git-native, human-auditable memory can provide the same temporal
correctness as a dedicated store while offering better *verifiability* of
revision, forgetting, and provenance.

Positioning (honest): git-native auditable memory (Springdrift, E-009),
confidence decay (Springdrift), procedural judge-free forgetting benchmarks
(ForgetEval, E-005), temporal-graph fields (Graphiti, E-024), and belief
revision (MnemeBrain/mnemosy) are all prior or adjacent. We therefore claim only
the *combination measured under identical budget*: verified bitemporal `as-of`
correctness, deletion/purge completeness across derived stores, and
provenance→action gating, packaged as a reproducible harness.

## 2. Related Work

**PENDING WP0/E6.** Single-screened prior-art matrix exists in
`data/literature/`; venue-wide search (ACL/ACM DL/IEEE/USENIX/OpenReview/arXiv)
and a second screening remain (completion-audit). Anchors already verified at
source: ForgetEval `b6053b7` (E-013), Springdrift `19b52b9` (E-040), Graphiti
`20a6728` (E-024), Mem0 `633b035` (E-025), Hindsight `1549987` (E-032).
Do not describe any capability as "first".

## 3. Design

Source: [architecture.md](./architecture.md). Principles: raw events immutable,
interpretations derived and versioned; valid time ≠ transaction time; current
truth is a view over history; retrieval hybrid and scoped before ranking; every
derived memory cites evidence; untrusted content is data, not policy; indexes
rebuildable from the ledger.

- **Event ledger** — typed `MemoryEvent` (`ingest/reconfirm/supersede/expire/
  purge`), append-only, JSONL or Git transaction adapter.
- **Bitemporal oracle** — `LifecycleOracle` folds events into `Belief`s; an
  independent `SqliteBitemporalOracle` is the cross-check.
- **Disposable projections** — exact/lexical/hashing-vector/learned-vector/graph
  indexes, rebuilt from materialized beliefs; RRF fusion then validity/authority/
  poisoning gates; evidence-backed `MemoryPacket`s.
- **Purge/crypto-purge** — JSONL tombstoning (with honest residual reporting) and
  the encrypted-payload `ProtectedEventStore` with per-belief key destruction
  (D-005, D-006).
- **Provenance-action gate** — signed, tenant-scoped ingestion quarantine
  separating write acceptance from sensitive-action activation.

## 4. Experimental Setup

Deterministic seeded generator produces typed histories; query truth is computed
independently of retrieval ranking. A natural-language renderer
(`nl_workload.py`) turns histories into conversational turns so opaque systems
answer against the same truth, removing the "BM25 gets structured terms" gap
(E-043). External systems are compared under identical backbone model,
temperature 0, retrieved-token budget, and pinned prompts, with sealed response
transcripts (D-010). Metrics: exact-state accuracy, evidence recall@K, stale/
superseded use rate, abstention, provenance coverage, purge completeness (see
evaluation-plan.md). ≥3 seeds (grid uses 10), per-condition bootstrap 95% CIs.

Baselines: recent/full context, BM25, append-only, last-write-wins, relational
bitemporal oracle, and — **PENDING E1 (D-010)** — Mem0 and Zep/Graphiti at
identical budget.

## 5. Results

### 5.1 Bitemporal correctness (RQ1)
The oracle held exact/recall/stale = 1/1/0 in all 90 conditions of a 3-profile ×
3-scale × 3-revision × 10-seed grid (E-049, strengthening E-044). Non-temporal
baselines degrade with churn: under the high-churn profile append-only reached
exact 0.255 / stale 0.662, recent/BM25 0.532 / 0.468, LWW 0.580 / 0.420 (E-049).

Against deployed systems under identical histories (forward-checkpoint
transaction-time replay, naturalized names), two distinct failure modes emerge:
**Mem0** consolidates to a single current value — good at transaction-scoped
current queries (transaction_as_of 0.949) but failing historical valid-time
(0.346), expiry (0.062), and purge (0.121); overall exact 0.607 and degrading
with scale (E-053, 48 cells). **Graphiti** preserves temporal edges — high
evidence recall (0.873) — but its default retrieval does not filter by
valid-time, returning superseded facts alongside current ones (stale-use 0.561,
exact 0.224; E-054, 6 cells). The oracle stays exact (1.0) across both.

Enabling Graphiti's *own* valid-time filter helps, but only partially and at a
cost: exact accuracy rises 0.224→0.318 and stale use falls 0.561→0.360, while
evidence recall drops 0.873→0.318 (E-057). The filter buys precision by
discarding evidence, and the categories that matter remain largely unanswered —
valid_time 0.093, expiry 0.067, purge 0.306 — against 1.0 for the oracle. Two
structural limits explain the ceiling: extracted `invalid_at` is often absent on
superseded edges (so stale facts satisfy the filter) and occasionally
contradictory (`invalid_at <= valid_at`), and `created_at`/`expired_at` record
wall-clock ingestion rather than the history's transaction time, so they cannot
express an `as-of` bound at all. Temporal *fields* are therefore not equivalent
to temporal *correctness* — the distinction this paper measures.

The ceiling is architectural, not an artifact of a weak extractor: swapping
`gpt-4o-mini` for `gpt-4o` on matched cells leaves the decisive categories
unchanged (valid_time 0.111 → 0.111, expiry 0.000 → 0.000) despite a 15×
costlier model, improving only transaction-scoped current queries (E-058).

(An earlier version of this experiment reported that filtering degraded every
metric; that measurement was invalidated by cross-run graph contamination and is
retracted (E-055). The numbers above come from re-runs with per-group isolation
verified directly in the database.)

### 5.2 Deletion / purge completeness (headline)
Both external systems fail deletion semantics under identical histories at the
answer level: Mem0 returns purged values (purge-category exact 0.121) and
expired values (0.062); Graphiti likewise (0.062, 0.000).

A residual scan of the backing stores explains why (E-056). After the same
purge, Temvera's rebuildable projections — Markdown, lexical, vector, graph —
contain **zero** occurrences of the purged payload; its only residual is the
append-only audit ledger (a documented limitation, D-005, addressed by the
encrypted profile's key destruction, E-033). Both external systems instead
retain the payload inside retrieval-reachable stores: Mem0 in exposed memories,
its Qdrant vector store, and its SQLite history; Graphiti in edge facts, entity
nodes, and raw episode bodies. The distinction is *where* deleted content
survives — an audit log that no query path reads, versus the serving index a
later query can resurface. Source-verified expectations frame this: Mem0
best-effort projection cleanup (E-025), Graphiti physical `remove_episode`
(E-024), Hindsight orphan→backfill (E-032). Counts are substring occurrences
over differently-shaped stores and are not magnitude-comparable.

### 5.3 Retrieval channels
Hard-channel necessity fixture isolates one necessary channel per category
(E-016). Learned dense retrieval resolved 10 held-out synonyms at recall@1 1.0
vs 0.0 for the alias-table-only hashing channel (E-050). Calibrated fusion gave
no held-out gain over fixed RRF (E-022); state-level decay did not dominate
rank-level decay (E-014).

### 5.4 External validity
On human-written LongMemEval conversations the same asymmetry appears: Mem0
retrieves the evidence for `knowledge-update` questions (current value after a
change) far better than for `temporal-reasoning` questions — gold-token recall
0.809 versus 0.188 (E-063). This supports the *characterisation* drawn from
synthetic histories, not any accuracy figure: scoring here is deterministic
substring/token presence over retrieved memories, deliberately separate from
LongMemEval's GPT-4o-judged QA metric (E-036), and the sample is 6 instances per
type. Mem0 also logged internal `UPDATE` failures during ingestion, which biases
against the knowledge-update side, so the real gap may be wider.

### 5.5 Provenance security
Signed, tenant-scoped gating blocked 0/4 activations while accepting 3/4 attacks
as inert data (E-017); it fails after trusted-signer compromise — provenance
proves origin, not signer honesty (E-023). Positioned as a mechanism study, not
a SOTA defense; adaptive/model-mediated attacks and GPU-bound defenses
(A-MemGuard, E-034) are out of scope.

## 6. Negative Results and Limitations

Preserved negatives: rank vs state decay (E-014), fusion calibration (E-022),
signer compromise (E-023), single-query learned saturation motivating the
expanded synonym set (E-050). Limitations: synthetic hand-specified operation
profiles; "contradiction density" approximated by operation mix and revision
count; no identical-budget end-to-end external result yet; single-screened
literature; human audit untested (protocol-only, D-009); purge guarantees cover
declared stores and tested failure points only.

## 7. Artifact and Reproducibility

Sealed local runs with canonical config, environment, source hash, and per-file
checksums; frozen synthetic dataset; aggregate verifier (E-045, E-047).
`pytest` and `ruff` pass on CPython 3.11. New systems-paper infrastructure:
`nl_workload.py`, `external_harness.py`, `synonym_eval.py`, the robustness grid
`lifecycle-grid-robust-v1`, and the learned-vector comparison. Public archive/DOI
deferred (D-009) until camera-ready; a flaky artifact tamper check is logged for
release hardening (E-051).
