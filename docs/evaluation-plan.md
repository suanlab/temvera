# Evaluation plan

## Evaluation layers

### 1. Operation correctness

Test ingest, reconfirm, supersede, merge, contradiction, expiry, purge, and
`as-of` queries against deterministic state-machine ground truth.

### 2. Retrieval quality

- Evidence Recall@K
- MRR and nDCG@K
- exact identifier recall
- temporal evidence recall
- multi-hop evidence coverage
- stale/superseded retrieval rate
- duplicate candidate rate

### 3. End-task quality

- factual answer accuracy
- temporal and multi-session reasoning
- knowledge-update accuracy
- calibrated abstention
- procedure reuse and repeated-failure avoidance
- task success with and without memory

### 4. Safety and governance

- memory-poisoning write acceptance
- attack activation after retrieval
- provenance forgery detection
- cross-tenant/scope leakage
- purge completeness across derived artifacts
- human audit and repair time

### 5. Efficiency

- write and retrieval p50/p95/p99
- index build and rebuild time
- bytes per raw and derived memory
- context tokens per answer
- extraction, embedding, and reranking cost
- consolidation backlog and index freshness

## Required baselines

1. recent context only
2. full context where feasible
3. session summaries
4. dense vector retrieval
5. BM25/full-text retrieval
6. hybrid retrieval with fixed RRF
7. append-only memory without revision
8. last-write-wins current state
9. relational bitemporal reference
10. selected external systems when licenses and reproducibility permit

## Experimental controls

- Pin model, prompt, embedding, tokenizer, and dataset versions.
- Use identical retrieved-token budgets across retrieval baselines.
- Separate retrieval recall from reader/LLM answer quality.
- Compare ANN results with exact search on a sampled query set.
- Report mean, dispersion, confidence intervals, and failure categories.
- Run at least three seeds for stochastic generation or judging.
- Store all configurations and raw outputs under `experiments/runs/`.
- Never tune on the final test set.

## Dataset groups

- Public conversational memory: LoCoMo and LongMemEval where licenses allow.
- Agent experience: LongMemEval-V2 or an equivalent trajectory benchmark.
- Procedurally generated lifecycle suite with exact state truth.
- Security suite containing trusted, untrusted, forged, and laundered sources.
- Internal synthetic workloads for scale, update rate, and filter selectivity.

The retrieval-identifiability split must contain named categories that isolate
channel necessity: alias/entity mismatch (exact failure), paraphrase with low
token overlap (lexical failure), historical valid-time distractors (temporal
failure), and evidence reachable only through derivation links (graph failure).
Report each category separately; a saturated aggregate does not validate a
hybrid design (evidence E-015).

## Success criteria for the first paper

The first artifact is ready only when it provides:

- deterministic generation and verification;
- at least four lifecycle operations beyond simple retrieval;
- a reproducible comparison against three meaningful baselines;
- error analysis for every primary metric;
- a public manifest with licensing and provenance for every data source;
- negative results and threats to validity.

## Current lifecycle-grid limitation

The v4 grid includes revision-only and seeded mixed reconfirm/expire/purge
profiles, with three seeds at each entity/revision condition. Bootstrap
intervals are computed only within fixed conditions, while cross-condition and
cross-profile summaries remain descriptive. The all-operation suite still uses
fixed topology. Two hand-specified profiles and three seeds do not establish
population-level robustness; contradiction density and broader operation
distributions remain future axes (E-043, E-044).
