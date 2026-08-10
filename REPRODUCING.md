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

The ForgetEval compatibility run additionally requires a clone of
`deeplethe/lethe` at commit
`b6053b7bdacc78a91b9ea4bb25f32edad278c495`. Learned-vector evaluation is not
part of the accepted artifact because its model was not downloaded. No API
keys, private data, or third-party source trees are included.

Repository-authored material and the fully synthetic fixture are distributable
under Apache-2.0. Public archive/DOI publication remains intentionally deferred;
the local package is not an archived release.
