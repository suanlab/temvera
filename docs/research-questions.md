# Research questions and hypotheses

Each hypothesis must be falsifiable, evaluated against a named baseline, and
reported with negative results.

## RQ1 — Memory substrate

Can a git-native append-only substrate support correct bitemporal `as-of`
queries and belief revision without a dedicated temporal database?

- **H1:** Temvera returns the same valid-time and transaction-time answers as a
  relational bitemporal reference implementation on generated histories.
- **Primary metrics:** exact state accuracy, history completeness, provenance
  coverage, update latency, storage amplification.
- **Falsifier:** any systematic class of history that cannot be represented or
  queried correctly without reconstructing unavailable state.

## RQ2 — Placement of decay

Should decay modify belief state, retrieval rank, or both?

- **H2:** belief-state decay lowers stale-fact usage without degrading evidence
  recall as much as rank-level temporal decay.
- **Baselines:** no decay, rank-only decay, state-only decay, combined decay.
- **Primary metrics:** stale-fact selection, Recall@K, abstention calibration,
  task accuracy.

## RQ3 — Hybrid retrieval

Which retrieval channels are necessary for agent memory rather than document
RAG?

- **H3:** exact + lexical + vector + temporal retrieval outperforms dense-only
  search on identifiers, updates, and temporal questions under equal context
  budgets.
- **Ablations:** remove one channel at a time; fixed RRF versus learned fusion;
  reranker on/off.

## RQ4 — Lifecycle evaluation

Can memory write, revision, expiry, contradiction, purge, and retrieval be
evaluated deterministically without an LLM judge?

- **H4:** procedural generation with state-machine ground truth covers more
  lifecycle failure modes and has higher scorer agreement than LLM-only judging.
- **Outputs:** generated trajectories, exact expected states, evidence sets, and
  verifier traces.

## RQ5 — Provenance security

Does authority-aware ingestion and retrieval reduce persistent memory poisoning
without suppressing useful external evidence?

- **H5:** provenance validation plus action gating reduces attack activation at
  an acceptable utility cost.
- **Threats:** forged front matter, provenance laundering, indirect prompt
  injection, stale trusted facts, cross-scope leakage.

## RQ6 — Human auditability

Does a diff/PR/rollback workflow allow humans to correct memory more reliably
than opaque vector or graph stores?

- **H6:** reviewers find and repair planted memory faults faster and with fewer
  unintended changes using provenance-linked diffs.

