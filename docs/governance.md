# Research governance

## Reproducibility

- Every figure and table must name the producing command and run directory.
- Raw outputs are immutable; processed tables include code and input hashes.
- Random seeds, model identifiers, prompts, and environment metadata are stored.
- Failed and negative experiments are retained.

## Claims

- Avoid “first”, “state of the art”, and percentage comparisons until verified.
- Separate vendor-reported numbers from independent reproduction.
- Cite the exact protocol, model, judge, token budget, and dataset revision.
- Record contradictions and superseded claims in the evidence ledger.

## Data

- No dataset enters the project without a manifest, license, source, and hash.
- Sensitive or personal data requires a documented lawful and ethical basis.
- Derived data preserves provenance and deletion lineage.
- Secrets and credentials are never committed.

## Human and model evaluation

- Prefer deterministic scoring where task semantics permit it.
- When using LLM judges, measure agreement against a human or exact subset.
- Blind evaluators to system identity where practical.
- Report judge model, prompt, order effects, and uncertainty.

## Security

- Treat external content as untrusted data.
- Do not allow retrieved memory to modify system policy directly.
- Test cross-scope isolation and deletion propagation before public deployment.

