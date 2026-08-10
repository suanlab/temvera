# Data directory

Do not commit downloaded datasets or generated bulk data by default.

Every dataset must have a manifest containing:

- canonical name and version;
- source URL and retrieval date;
- license and redistribution terms;
- cryptographic hashes;
- preprocessing command and code revision;
- split policy and leakage checks;
- personal/sensitive data assessment.

Suggested layout:

```text
data/
├── manifests/
├── literature/   # review search log and screening/extraction matrix
├── raw/          # ignored
├── interim/      # ignored
├── processed/    # ignored unless deliberately released
└── fixtures/     # small deterministic test samples
```

`fixtures/lifecycle-v0/` is a byte-reproducible, fully synthetic split created
with `temvera freeze-dataset ... --entities 8 --revisions 4`. Its verifier
checks hashes, event counts, and cross-split identifier isolation. The embedded
card permits redistribution under Apache-2.0. No third-party dataset is
included or relicensed.
