# Experiments

Each experiment receives an immutable run directory. The lifecycle runner also
captures environment and source hashes; external compatibility runners capture
the pinned upstream commit and file checksums. Exact filenames may differ by
runner, but every run must contain configuration, metrics, case-level
predictions, and checksums:

```text
experiments/runs/<date>-<experiment>-<short-hash>/
├── config.json
├── environment.json        # when the runner depends on the local environment
├── metrics.json
├── predictions.json or predictions.jsonl
└── checksums.json
```

The run README must state the hypothesis, command, inputs, expected outcome,
actual outcome, and interpretation. Large outputs should be stored in artifact
storage and referenced by checksum.

Small versioned configurations live in `experiments/configs/`. Reproduce the
lifecycle smoke configuration with:

```bash
temvera generate /tmp/temvera-smoke --seed 17 --entities 4 --revisions 3
temvera benchmark /tmp/temvera-smoke
```

Create an immutable, checksummed run directory from the versioned config:

```bash
temvera run-experiment experiments/configs/lifecycle-smoke.json \
  experiments/runs
```

The pinned ForgetEval compatibility run is stored at
`experiments/runs/forgeteval-temvera-lexical-seed42/`. It was produced through
the following command, which refuses to overwrite an existing output and
rejects an unexpected upstream commit:

```bash
temvera forgeteval-compatibility \
  experiments/configs/forgeteval-compatibility.json \
  /path/to/lethe \
  experiments/runs/forgeteval-temvera-lexical-seed42
```
