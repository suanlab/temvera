# VLDB EA&B submission plan

> Decision D-014 (2026-08-14). Target: PVLDB **Experiments, Analysis & Benchmark**
> track, monthly rolling deadlines; VLDB 2027 closes 2027-03-01, abstracts on the
> 25th of the prior month. No arXiv preprint (user decision).
> **Verify the CFP directly before submitting** — the requirements below come
> from the 2027 call as read on 2026-08-14 and may change.

## Why this track

EA&B rewards exactly what every other venue penalised. It *requires* releasing
all experimental data and software and submitting to the PVLDB Reproducibility
Committee, which makes our sealed runs, checksums, and evidence ledger a scored
criterion rather than a footnote. It exists for rigorous comparison of existing
systems, so declining to claim novelty is the track's premise rather than a
weakness. And 12 pages excluding references leaves room for the depth reviewers
asked for.

## Done

- **Fragment-of-semantics section** (paper §4). Classifies support into
  `absent` / `prose` / `off` / `mismatch` / `yes` across six capabilities a
  bitemporal point query requires, and uses it to explain the measurements
  rather than merely tabulate them. Three entries carry the argument: Graphiti's
  `created_at` is wall-clock so no as-of predicate is expressible at all;
  LangMem stores validity *in prose*, legible to a reader and invisible to a
  query planner, which a capability checklist would score as support; and
  supersession-closes-interval is the axis on which the two design families
  separate.
- **EA&B category tag** in the title, as the call requires.
- **Reference implementation demoted.** Our substrate is no longer presented as
  a compared system; an EA&B paper that ranks the authors' own system invites a
  conflict-of-interest reading, and review already found it enjoyed protocol
  advantages.
- **Three figures and 20 citations**, all generated from sealed runs.

## Gaps, in priority order

### G1 — System count (highest risk)
Three systems where DB reviewers expect six to eight. Adapter work is cheap; the
blocker is infrastructure, and we have already scouted it:

| Candidate | Blocker | Effort |
|---|---|---|
| Zep cloud | credentials only | low, if an account is available |
| Letta | requires PostgreSQL; exposes agent-messaging, not retrieval, so it is not comparable under this scorer without a protocol change | medium–high |
| Hindsight | PostgreSQL + pgvector, multi-service application | high |
| Cognee | pip-installable; local backends not yet verified | unknown, worth 30 min to check |

Rootless PostgreSQL is feasible — we already run Neo4j from a tarball without
Docker — but pgvector needs compiling against server headers. **Recommended
order:** Cognee (cheap to check), then Zep cloud, then PostgreSQL once and
Hindsight after it.

### G2 — No scale, latency, or cost dimension
VLDB reviewers expect them and we report none. Largest grid is 20 cells over
histories of 3–8 entities. Needed: per-operation ingest and query latency, token
and dollar cost per history, and at least one order-of-magnitude scale sweep.
Instrumentation is straightforward; the sweep costs API budget. This also closes
the reviewer complaint that an earlier draft called one extractor "15× costlier"
with no measurement behind it.

### G3 — Workload realism
One attribute per entity (`home city`) makes cosine retrieval degenerate by
construction, which review flagged as interacting with the budget effect. Adding
three to five attributes per entity, with values that are not all one semantic
class, is cheap (generator change) and removes a standing objection.

### G4 — Reproducibility packaging for the committee
Our position is strong but must be stated precisely: **scoring and aggregation
are fully recomputable offline** from the sealed per-case `transcript.jsonl`
files, so the committee can verify every reported number without API keys.
Only *regenerating* runs needs an OpenAI key, a Neo4j server, and — for LangMem
— a second virtualenv, because it requires `openai>=3` while the pinned Mem0 and
Graphiti require `openai==1.x`. Ship a one-command offline verification path and
say plainly which numbers it covers.

**Resolved (2026-08-17):** the LongMemEval split we use is MIT-licensed,
verified against the published dataset metadata (E-074). The release requirement
is therefore satisfiable without dropping the external-validity section, and the
dataset could be shipped with the artifact if the committee wants it
self-contained. We still download rather than redistribute it.

## Formatting: done

The official template is `vldbproceedings/VLDB-Template`, not the third-party
`cwida/pvldbstyle` an earlier revision of this plan named. There is no separate
`vldb.cls`: the template is ACM `acmart` with `[sigconf, nonacm]`, plus a
**`pvldb.sty`** that emits the VLDB front matter — the reference-format line, the
CC BY-NC-ND footnote, and a conditional artifact-availability block — from a
single `\vldbtopmatter` call after `\maketitle`. `paper/` vendors `pvldb.sty`,
`acmart.cls` (v2.19, the version the template pins), and
`ACM-Reference-Format.bst` so the build does not depend on the local TeX
distribution's `acmart` version.

Two settings are review-version choices to revisit at camera-ready:
`\vldbpagestyle` is `plain` (page numbers on) and `\vldbavailabilityurl` is
empty, which deliberately suppresses the artifact-availability block — it should
carry the artifact URL once the work is no longer anonymous.

The submission builds clean at **7 pages against the 12-page EA&B limit**, with
no undefined references or citations, and `pdftotext` finds no author,
institution, or project name anywhere in the output.

## Artifact package: done

`temvera artifact-package` emits a deterministic, checksum-manifested archive
(310 files, 0.7 MB) that `verify-artifact-package` validates, covering the
source tree, tests, docs, fixtures, experiment configs, and every accepted
sealed run. Two exclusions are explicit and tested rather than incidental:
`data/raw` (third-party datasets we download rather than redistribute — this is
what keeps the archive at 0.7 MB instead of 83 MB) and `__pycache__`, whose
interpreter-dependent bytes would break the byte-for-byte determinism the
manifest promises. The paper source is not packaged; it is submitted separately.

## Sequencing

Rolling deadlines mean we choose when to submit. Targeting a **January or
February 2027 cycle** leaves time for G1–G3 without racing, and keeps the March
close as a fallback rather than a plan.

1. G3 (generator change, no API cost) and G4 (packaging) — immediate, offline.
2. G2 instrumentation, then a scale sweep sized to budget.
3. G1 as far as infrastructure allows; two additional systems would put us at
   five, which is defensible even if six is the norm.

## Standing risk

Several causal explanations bottom out in LLM extraction quality rather than
data-management design — `invalid_at` is unset because the extractor did not set
it, not because the schema forbids it. A DB reviewer may read that as off-topic.
The paper now states this explicitly in §4 and frames it as a claim about the
pipeline that populates a temporal store: for LLM-backed systems the extraction
layer, not the schema, is the binding constraint. That is a defensible framing,
but it is a framing, not new evidence, and it should not be oversold.
