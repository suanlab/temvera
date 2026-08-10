# Temvera lifecycle v0 dataset card

## Summary

This is a fully synthetic, seed-frozen event stream for testing bitemporal
ingest and supersession semantics. It contains no conversations, model output,
or personal data. Version: `0.1.0`.

## Splits and intended use

Train and development may be used for implementation and threshold selection.
The test split is evaluation-only. Each split uses disjoint generated entity
labels and a fixed seed recorded in `manifest.json`.

## Limitations

Template labels do not model natural-language ambiguity, entity resolution,
realistic update rates, or social context. Scores measure mechanism correctness,
not real-world agent quality. Reconfirmation, expiry, purge, and attacks are
covered by deterministic test fixtures but are not yet included in this v0
bulk split.

## License and redistribution

permitted under the repository Apache-2.0 license. Third-party datasets are not included or covered.
