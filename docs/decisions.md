# Decision log

## D-001 — Preserve raw events

- **Status:** accepted
- **Decision:** Raw observations and interactions are append-only. Summaries,
  beliefs, and indexes are derived artifacts.
- **Reason:** Enables reprocessing, audit, deletion propagation, and comparison
  of extraction policies.

## D-002 — Model two time axes

- **Status:** accepted
- **Decision:** Separate valid/event time from record/transaction time.
- **Reason:** Current-state overwrites cannot answer what was true versus what
  the agent knew at a past point.

## D-003 — Start with dual substrates

- **Status:** accepted
- **Decision:** Implement a Git-native research substrate and a relational
  bitemporal oracle.
- **Reason:** The relational implementation prevents the project from declaring
  Git superior without correctness and performance evidence.

## D-004 — Temvera working name

- **Status:** superseded by D-007
- **Decision:** Use Temvera as the working name, pending formal clearance.
- **Reason:** Preliminary web search found no direct same-category collision,
  but package, domain, and trademark clearance is incomplete.

## D-005 — Immutable metadata does not justify immutable sensitive payloads

- **Status:** accepted; narrows D-001
- **Decision:** Keep non-sensitive event metadata and deletion receipts
  append-only, but do not claim physical purge while private payload remains in
  the JSONL ledger. A release design must make payload erasure independently
  verifiable, for example through encrypted payload separation and key
  destruction.
- **Reason:** Audit history and deletion lineage are required, but retaining the
  content being deleted would violate the research program's security goal.

## D-006 — Keep encryption keys outside the Git substrate

- **Status:** accepted for the experimental protected profile
- **Decision:** Encrypt subject, attribute, value, and source references with a
  per-belief AES-256-GCM key. Commit metadata and ciphertext, never keys. A
  cryptographic purge destroys the key and records its hash in a non-sensitive
  receipt.
- **Reason:** Rewriting distributed Git history cannot prove removal from
  clones. If a key was never committed, key destruction makes retained
  ciphertext unusable without destroying the audit log.
- **Limit:** This is not proof of deletion from RAM, swap, upstream sources, or
  unauthorized key backups.

## D-007 — Retain Temvera as the project name

- **Status:** accepted 2026-07-16 by user decision
- **Decision:** Retain Temvera as the project name for repository metadata and
  future release preparation.
- **Reason:** The preliminary collision screen found no exact same-category
  use. This is a naming decision, not legal trademark clearance or reservation.

## D-008 — License repository-authored material under Apache-2.0

- **Status:** accepted 2026-07-16 by user decision
- **Decision:** Apply Apache-2.0 to repository-authored code, documentation,
  fully synthetic fixtures, and accepted locally generated experiment outputs.
- **Reason:** A permissive license with an explicit patent grant supports
  reproducible research and reuse. Third-party artifacts retain their own
  licenses and are not relicensed or redistributed.

## D-010 — Authorize external-system reproduction under API-only resources

- **Status:** accepted 2026-07-16 by user decision (systems-paper plan approval)
- **Decision:** Permit LLM-API use to reproduce external memory systems
  (Mem0, Zep/Graphiti) under identical budgets, and seal their API-response
  transcripts for reproducibility. Only fully synthetic Temvera histories are
  sent; no private or redistribution-restricted data. Third-party system source
  trees are run for comparison, not relicensed or redistributed.
- **Reason:** Identical-budget external comparison is the systems paper's
  largest gap; API-only resources make Mem0 and Zep/Graphiti feasible without
  GPUs. Narrows the "external systems unexecuted" bound of D-009.
- **Limit:** GPU-bound baselines (A-MemGuard, MemIncept, learned rerankers) stay
  out of scope; security remains a deterministic mechanism study.

## D-011 — Authorize learned dense-retrieval baseline model download

- **Status:** accepted 2026-07-16 by user decision (systems-paper plan approval)
- **Decision:** Permit downloading a public CPU/ONNX embedding model (e.g.
  `bge-small`) to restore the learned dense-retrieval baseline excluded in E-038.
- **Reason:** fastembed runs on CPU, so the learned-vector channel can be
  evaluated without GPUs. Lifts the learned-model portion of D-009's deferral.
- **Limit:** DOI/public-archive publication remains deferred under D-009 until
  separately authorized at camera-ready.

## D-009 — Bound the remaining evaluation scope

- **Status:** accepted 2026-07-16 by user decision
- **Decision:** Publish the human-audit protocol without recruiting
  participants; keep learned-model download and public archive/DOI publication
  deferred until separately authorized.
- **Reason:** These actions require ethics, external model, or publication
  authority beyond the local deterministic artifact.

## D-012 — No upstream bug filing; human audit study is future work

- **Status:** accepted 2026-08-12 by user decision
- **Decision:** Do not file the Mem0 defect upstream. Keep the analysis in
  `docs/upstream-bug-mem0-update-keyerror.md` as internal evidence for E-065,
  which explains why the reported Mem0 numbers are conservative. The human
  audit study (RQ4) is not run for this submission and is reported as future
  work; D-009's protocol-only scope therefore stands unchanged.
- **Reason:** The defect report is a routine, non-security OSS issue whose
  filing is optional, and the intermittent reproduction weakens it. Ethics
  review or a documented exemption plus a pilot and power analysis cannot
  responsibly fit before the ICLR deadline, and the protocol itself requires
  that sequence before recruitment.
- **Limit:** This is a scope decision for one submission, not a finding that
  the defect is unimportant or that the study is infeasible later.
