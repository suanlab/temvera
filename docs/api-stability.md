# API Stability Review

## Status

Version `0.0.1` is a research API. Apache-2.0 governs use, but nothing is
promised stable before a schema migration policy and compatibility suite are
approved. The CLI is the
preferred reproducibility surface; Python imports support experiments and may
change.

## Deliberately public Python surface

`temvera.__all__` exports typed events and beliefs, lifecycle and SQLite
oracles, JSONL/Git-compatible stores, protected storage, lexical and hashing
vector indexes, memory packets, decay primitives, and deterministic generators.
All other modules—including experiment runners, governance prototypes, hybrid
fusion, literature tooling, and learned embeddings—are experimental internals.

## Compatibility risks before 0.1

- `MemoryEvent` JSON has no explicit schema-version field.
- Operation and authority enums are serialized by value; renaming is breaking.
- Purge receipts and recovery journals need a documented migration policy.
- Query ordering is deterministic but not yet declared as a compatibility
  contract.
- CLI output JSON lacks a shared envelope version.
- Optional cryptography and learned-vector dependencies require separate test
  matrices.

## Release gate

Before declaring 0.1, add golden serialization fixtures, backward-read tests,
CLI schema versions, a deprecation policy, and supported-Python CI. This review
is complete; API stabilization itself is not.
