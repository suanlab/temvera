# Defensible Contribution Statement

Temvera is a research prototype for testing whether a rebuildable, file- and
Git-compatible agent-memory substrate can reproduce explicit bitemporal state
while making revision, purge, provenance, and retrieval decisions auditable.
It does not claim to be the first Git-backed, temporal, or judge-free agent
memory system.

## Nearest prior work

- ForgetEval already provides seeded lifecycle generation and deterministic
  top-k substring scoring for supersession, decay, amnesia, purge, and drift.
- Springdrift already combines append-only memory, auditability, and Git-backed
  recovery.
- Graphiti already represents temporal graph facts using creation, validity,
  invalidity, and expiry timestamps.
- Mem0 already records add/update/delete history alongside a mutable vector
  memory store.
- MemLineage motivates cryptographic lineage and action gating, while MINJA
  demonstrates query-only persistent-memory poisoning.
- Hindsight already combines fact/belief separation, temporal graph, hybrid
  retrieval, invalidation archives, history, audit logs, and derived-deletion
  repair; Mem2ActBench already joins memory evolution and tool use.
- A-MemGuard and MemIncept provide current poisoning defense and adaptive
  injection baselines.

## Measurable delta

The prototype's defensible unit is the combination of:

1. an operation-level lifecycle model with separate valid and transaction
   times, checked against an independent SQLite oracle;
2. byte-deterministic reconstruction of Markdown, lexical, vector, and graph
   projections from an append-only event log;
3. purge receipts and an encrypted-payload profile whose per-belief key
   destruction is tested after a Git clone;
4. provenance-aware retrieval plus tenant-scoped signed action gating; and
5. deterministic fixtures that preserve negative results for decay, channel
   ablation, fusion calibration, and compromised trust roots.

These are mechanism results on synthetic fixtures, not evidence of production
scale, human-audit superiority, benchmark leadership, or complete deletion from
all physical media.

## Falsification and remaining gates

The central claim fails if any generated lifecycle yields a different state
from the independent oracle, if projection rebuilds differ byte-for-byte, or if
a purged belief remains reachable in a declared derived store. External claims
remain gated on identical-budget runs against released baselines, frozen public
datasets, and statistical evaluation. Temvera and Apache-2.0 were selected in
D-007/D-008. Trademark legal clearance remains separate; human participants,
learned-model download, and public DOI are outside the approved local-artifact
scope under D-009.
