# Research Program Completion Audit

Status is based on repository artifacts and executable checks, not intent.

| Requirement | Evidence | Status |
|---|---|---|
| Primary-source prior-art matrix | `data/literature/`; pinned ForgetEval, Graphiti, Mem0, Hindsight, A-MemGuard, and experience-following artifacts | partial: venue-wide search and second screening remain |
| Defensible novelty boundary | `docs/contribution-statement.md`; evidence ledger E-005, E-009, E-024, E-025 | complete for the current prototype scope |
| Deterministic lifecycle oracle | generator, in-memory oracle, independent SQLite oracle, equivalence tests, corrected valid/transaction-time and empty purge cases | complete for implemented operation classes; reconfirmation metadata is state-tested rather than query-metric-scored |
| Frozen lifecycle dataset | `data/fixtures/lifecycle-v0`; byte-reproducibility, checksum, count, tamper, and split-leakage tests; Apache-2.0 manifest | complete for the fully synthetic v0 fixture |
| Rebuildable local substrate | append-only events and deterministic Markdown/lexical/vector/graph projections | complete at prototype scale |
| Purge and deletion lineage | purge receipts, derived-store checks, encrypted key-destruction clone test, fault injection and journal recovery | partial: no claim over undeclared backups, third-party stores, or every crash point |
| Retrieval and decay evaluation | 2-profile × 3-seed × 3-scale × 3-revision grid, 3-seed all-operation suite, hard-channel fixture, 384-cell decay sweep, disjoint fusion comparison, efficiency run; sealed configs/environments/checksums | complete as synthetic mechanism studies; only two hand-specified operation profiles and external validity remains |
| Provenance security | threat model, signed gate, laundering checks, adaptive bypass report | complete as deterministic mechanism study |
| Closest-system comparison | ForgetEval 100-case compatibility run; source-level Graphiti, Mem0, Hindsight, and Springdrift extraction; Springdrift fallback experiment audit | partial: identical-budget third-party system score reproduction remains; Springdrift fallback is explicitly not counted |
| Human audit study | preregisterable protocol, seeded planted-fault generator, crossover assignment, deterministic scorer | protocol-only scope complete under D-009; no participant result or RQ4 empirical claim |
| Release package | Apache-2.0, retained Temvera name, ten-run allowlist, aggregate verifier, deterministic local archive, reproduction guide, API review | complete for approved local scope; public archive/DOI intentionally deferred under D-009 |

## Verification environment

The current host provides Python 3.10 while `pyproject.toml` requires Python
3.11 or newer. A temporary CPython 3.11.15 environment was therefore created
outside the repository. The licensed candidate passed 89 tests, Ruff, isolated
package builds, clean-wheel CLI smoke tests, frozen-data verification, and the
ten-run aggregate artifact verifier. Exact candidate hashes are recorded in
`docs/release-verification.md`.

The approved local-artifact program is complete. The single-reviewer literature
limitation and unexecuted external systems remain explicit threats, not hidden
completion claims. Human
participants, learned-model download, and public DOI publication are deferred
by D-009 and must not be reported as completed empirical studies.
