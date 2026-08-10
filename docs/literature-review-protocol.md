# Prior-art review protocol

## Scope

This review asks which published systems or benchmarks implement or evaluate
persistent agent memory with temporal revision, forgetting, provenance,
poisoning defenses, or operation-level ground truth. The search window starts
at 2020-01-01 and remains open until the preregistration freeze.

## Sources and query families

Search ACL Anthology, ACM Digital Library, IEEE Xplore, USENIX, OpenReview, and
arXiv. Record the exact query, date, result count, and export location in
`data/literature/search-log.csv`. Combine `agent OR assistant` and `memory`
with each family:

1. `temporal OR bitemporal OR update OR revision OR stale`
2. `forget OR expiry OR deletion OR lifecycle`
3. `provenance OR lineage OR poisoning OR injection`
4. `benchmark OR evaluation OR judge-free OR deterministic`

Forward- and backward-chain every included peer-reviewed paper. Search source
code and artifact pages separately; do not infer implementation details from
abstracts.

## Screening

Include primary work that implements or evaluates persistent memory used by an
LLM agent and addresses at least one query family. Exclude surveys (retain for
citation chaining), model-weight unlearning without external agent memory,
ordinary document RAG without state changes, and sources without enough detail
to locate a primary artifact. Record one row per work in
`data/literature/studies.csv`; preserve exclusions and contradictory evidence.

One reviewer screens all records and re-screens a deterministic 10% sample
selected by SHA-256 of the canonical identifier. A second reviewer should
resolve disagreements before novelty lock. Until then, `review_state` remains
`single_screened` and novelty claims remain hypotheses.

Same-reviewer second-pass decisions are recorded separately in
`data/literature/rescreen-log.csv`; they do not change `review_state` to a
dual-screened status or substitute for an independent reviewer.

## Extraction and freeze

Extract substrate, time semantics, operations, scorer type, datasets, security
model, audit mechanism, artifact URL, license, and evidence-ledger IDs. Freeze
the CSV files with SHA-256 checksums and the repository revision. A contribution
is defensible only when its nearest work, measurable delta, and falsifying
experiment are all present in the matrix.
