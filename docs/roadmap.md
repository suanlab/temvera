# Roadmap

## Phase 0 — Prior-art and novelty lock

- [ ] Verify every novelty claim against primary papers and source code.
- [ ] Complete the evidence ledger with claim, source, support, and caveat.
- [ ] Reproduce the closest lifecycle and belief-revision baselines.
- [x] Retain the Temvera project name after a preliminary package/domain/web
  collision screen. (not legal trademark clearance or reservation)
- [x] Select Apache-2.0 and an Apache-compatible contribution policy.

**Exit:** one-page defensible contribution statement with no unverified
“first” claims.

## Phase 1 — Deterministic lifecycle benchmark

- [x] Define the initial entity/attribute state machine.
- [x] Generate deterministic write, revision, reconfirmation, expiry, and purge cases.
- [x] Implement initial exact-state, evidence-recall, and stale-use scoring.
- [x] Reproduce compatible categories from existing forgetting benchmarks.
  (ForgetEval generator pinned at `b6053b7`; the deterministic Temvera lexical
  adapter passed 85/100 generated cases. Published third-party system scores
  remain outside this compatibility result.)
- [x] Implement verifiable dataset cards and frozen train/development/test
  split tooling under Apache-2.0.

**Exit:** one-command reproducible benchmark with baseline report.

## Phase 2 — Dual reference implementations

- [x] Git-compatible canonical event and Markdown belief store.
- [x] Independent persistent SQLite bitemporal correctness oracle.
- [x] Disposable persisted lexical and dependency-free hashing-vector projections.
- [x] Initial provenance-linked lexical memory packet generation.
- [x] Event round-trip and byte-deterministic projection rebuild tests.
- [x] Experimental encrypted-payload profile with per-belief cryptographic
  erasure and Git-clone verification.

**Exit:** operation-equivalence tests pass on generated histories.

## Phase 3 — Retrieval and decay experiments

- [x] Initial exact, lexical, dependency-free vector, temporal, and graph
  mechanism ablations, including category-specific necessity fixtures.
- [x] Fixed RRF versus development-only calibrated fusion on disjoint hard
  variants; no held-out gain observed.
- [x] Rank decay versus belief-state decay. (384 deterministic cells complete;
  state decay did not dominate and the negative result is preserved)
- [x] Initial local context-budget and p50/p95/p99 latency Pareto analysis.

**Exit:** preregistered primary experiment completed with error analysis.

## Phase 4 — Provenance security

- [x] Initial explicit threat model and seeded mechanism-isolation attack generator.
- [x] Signed authority- and tenant-aware ingestion quarantine and action gating.
- [x] Initial missing-provenance and laundering detection.
- [x] Deterministic action-gating ASR and benign-utility metrics.

**Exit:** security report with attack success, utility, and bypass analysis.

## Phase 5 — Release

- [x] Deterministic local artifact packaging with an internal checksum manifest.
- [ ] Public archival/DOI. (intentionally deferred under D-009; not required for
  the approved local-artifact scope)
- [x] Anonymous reproducibility instructions for the local artifact.
- [x] Initial paper draft, frozen-data card, and model-applicability card.
- [x] Public API stability review. (review complete; 0.1 stabilization gates
  remain open)
