# Reproducing the Local Artifact

The accepted artifact is dependency-free except for development checks and the
optional cryptographic tests. Use CPython 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
pytest
ruff check .
temvera verify-dataset data/fixtures/lifecycle-v0
temvera verify-artifacts experiments/accepted-runs.json experiments/runs
```

Regenerate the primary local lifecycle studies into new immutable directories:

```bash
temvera run-experiment experiments/configs/lifecycle-smoke.json /tmp/runs
temvera lifecycle-grid experiments/configs/lifecycle-grid.json /tmp/runs/grid
temvera lifecycle-operation-suite \
  experiments/configs/lifecycle-operation-suite.json /tmp/runs/operations
temvera security-experiment \
  experiments/configs/security-evaluation.json /tmp/runs/security
```

Outputs refuse overwrite and contain canonical configuration, environment,
source-tree hash, and per-file checksums. Compare regenerated metrics rather
than expecting byte-identical `environment.json`, which records creation time
and platform.

## External-system experiments (require credentials)

Sections of the paper that compare deployed systems need resources the local
artifact deliberately does not bundle. Everything else above runs offline.

| Experiment | Command | Requires |
|---|---|---|
| Mem0 comparison | `temvera external-mem0 <config> <out>` | `OPENAI_API_KEY` |
| Graphiti comparison | `temvera external-graphiti <config> <out>` | `OPENAI_API_KEY`, Neo4j 5.26 at `NEO4J_URI` |
| Purge residual | `temvera purge-residual <config> <out>` | both of the above |
| LongMemEval validity | `temvera longmemeval-eval <config> <out>` | `OPENAI_API_KEY`, dataset downloaded to `data/raw/` |
| Learned dense channel | `temvera vector-synonym-compare <out>` | model download (CPU only) |

Set `OPENAI_API_KEY`, and for Graphiti `NEO4J_URI`, `NEO4J_USER`,
`NEO4J_PASSWORD`. A rootless Neo4j (JDK 21 + the community tarball) is
sufficient; Docker is not required. Wall-clock is dominated by per-turn LLM
extraction: roughly 1-2 h for a 20-cell grid and 35-40 min per instance on the
distractor-laden LongMemEval split.

LongMemEval data is **not redistributed here**; download it from the official
release. Its code is MIT, but the benchmark-data licence is unresolved
(evidence ledger E-001, E-036), so confirm your own terms of use. Our scorer is
deterministic substring/token presence over retrieved memories and is **not**
the benchmark's LLM-judged QA metric; the two must not be compared.

Regenerate the paper figures from sealed runs with
`python scripts/make_figures.py`.

The ForgetEval compatibility run additionally requires a clone of
`deeplethe/lethe` at commit
`b6053b7bdacc78a91b9ea4bb25f32edad278c495`. No API keys, private
data, or third-party datasets are included in this repository.

Repository-authored material and the fully synthetic fixture are distributable
under Apache-2.0. Public archive/DOI publication remains intentionally deferred;
the local package is not an archived release.
