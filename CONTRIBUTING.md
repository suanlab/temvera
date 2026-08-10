# Contributing

Temvera is currently a research-stage project. Contributions should improve a
falsifiable hypothesis, reproduce prior work, add a deterministic verifier, or
strengthen the reference implementation.

## Change checklist

- Describe the research question or engineering problem.
- Link supporting primary sources where applicable.
- Add tests or explain why the change is documentation-only.
- Record experiment commands and raw outputs.
- Update the evidence or decision ledger when conclusions change.
- Avoid performance claims without a reproducible comparison.

## Local checks

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
```

By submitting a contribution, you agree that it is your original work (or that
you have the right to submit it) and that it is licensed under Apache-2.0 on
the same terms as the repository. Do not submit third-party code or data unless
its license, provenance, and redistribution compatibility are documented.
