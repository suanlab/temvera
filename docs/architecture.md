# Reference architecture

## Design principles

1. Raw events are immutable; interpretations are derived and versioned.
2. Event time and record time are distinct.
3. Current truth is a view over history, not an overwritten row.
4. Retrieval is hybrid and scoped before ranking.
5. Every derived memory points to supporting evidence.
6. Untrusted content is data, never executable policy.
7. Derived indexes must be rebuildable from the source ledger.

## Logical model

```text
raw event
  ├── episode
  ├── fact/belief ──supersedes──> prior fact/belief
  ├── procedure
  └── entity/relation

Each derived record:
  provenance → source event(s)
  valid time → when it is true
  record time → when the system learned it
  authority → who or what supports it
  confidence → calibrated belief strength
```

## Write path

```text
capture → authenticate → classify trust → append raw event → enqueue
        → extract candidates → resolve entities → compare current beliefs
        → insert/reconfirm/supersede/dispute → index → consolidate
```

Raw capture is synchronous. Extraction, embedding, entity resolution, and
consolidation are asynchronous and idempotent.

## Retrieval path

```text
query
  → scope/ACL + intent + entity + temporal parsing
  → exact | lexical | vector | temporal | graph candidate retrieval
  → rank fusion
  → validity, authority, and poisoning gates
  → reranking and diversity control
  → evidence-backed memory packet
```

Raw scores from heterogeneous retrievers are never compared directly. Initial
experiments use Reciprocal Rank Fusion; learned fusion is considered only after
relevance feedback is sufficient.

## Storage profiles to evaluate

### Profile A — Git-native research substrate

- Markdown/JSON records
- Git history as transaction-time ledger
- SQLite FTS/vector index as disposable local projection
- Human diff, review, signing, and rollback

### Profile B — Relational reference

- SQLite for the dependency-free correctness oracle; PostgreSQL is deferred to
  the concurrency and operational-baseline phase
- append-only event table
- bitemporal fact versions
- GIN full-text and JSONB indexes
- pgvector HNSW

The SQLite implementation is the current correctness oracle, not an operational
or concurrency baseline. A later PostgreSQL profile must be treated as a real
competitor, not an assumed loser. Temvera must demonstrate a measurable
advantage rather than rely on a philosophical preference for files or Git.

## Memory record minimum fields

```yaml
id: stable identifier
kind: episodic | semantic | procedural | preference | task_state
subject: canonical entity or scope
content: human-readable assertion
valid_from: event-time lower bound
valid_to: event-time upper bound or null
recorded_at: transaction time
status: active | superseded | disputed | expired | deleted
confidence: 0..1
authority: system | verified_tool | user | external | inferred
sources: immutable source references
supersedes: prior memory identifier or null
policy_version: ingestion and retrieval policy version
```

## Non-goals for the first prototype

- A general-purpose vector database
- Training a foundation model
- Claiming human-like cognition
- Replacing transactional application databases
- Optimizing for billion-vector scale before correctness is established

## Purge boundary and protected profile

The v0 JSONL ledger removes purged beliefs from rebuilt Markdown and lexical
projections, but immutable event payloads remain in `events.jsonl`. Therefore it
does **not** yet satisfy physical erasure of private data. Tests report residual
occurrences instead of treating a tombstone as deletion. A release-capable
design must separate encrypted payloads from immutable metadata and destroy the
relevant keys, or use a redaction-capable raw store while retaining a
non-sensitive deletion-lineage receipt.

The experimental `ProtectedEventStore` implements the first option with
AES-256-GCM and one key per belief. Git receives append-only metadata and
ciphertext; `.temvera-keys/` is deny-all ignored. Destroying a key makes current
and historical committed ciphertext unreadable while preserving a receipt that
contains only identifiers, timestamp, and the destroyed key's hash. This does
not erase plaintext from independent systems that saw it before ingestion,
memory, swap, logs, or backups of the key directory. Key backup and destruction
policy must therefore be part of any deployment claim.

Current-tree redaction and multi-key cryptographic purge use plaintext-free
durable journals. If receipt persistence fails after ledger replacement or key
destruction, `recover_redactions()` or `recover_crypto_purge()` completes the
receipts idempotently. This is tested crash recovery at declared failure
points, not atomic mutation across filesystems, old Git clones, or backups.
