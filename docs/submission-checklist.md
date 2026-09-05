# PVLDB Volume 20 — October 2026 cycle

| | |
|---|---|
| **Abstract due** | **2026-09-25, 17:00 Pacific** — mandatory, missing it is a desk rejection |
| **Paper due** | **2026-10-01, 17:00 Pacific** |
| Reviews expected | around 2026-11-15 |
| System | <https://cmt3.research.microsoft.com/PVLDBv20_2027/> (volume 20, **not** the v19 site) |
| Track | Experiment, Analysis & Benchmark |

## To paste into CMT

**Title** — the category tag is required in the CMT title as well as the PDF:

```
Temporal Fields Are Not Temporal Correctness: Measuring Bitemporal and Deletion
Semantics in Deployed Agent Memory [Experiment, Analysis & Benchmark]
```

**Abstract**: `paper/abstract.txt`, plain text, no LaTeX or citation markers.

**Author**: Suan Lee, School of Computer Science, Semyung University, Jecheon,
South Korea. Contact address is currently personal; substitute an institutional
one if preferred.

**Reproducibility package** (required *at initial submission* for volume 20, not
at camera-ready): <https://github.com/suanlab/temvera> — instructions in the
README and `REPRODUCING.md`, frozen snapshot at the `pvldb-eab-v1` release.

## Only the author can do these

- [ ] Register in CMT and **declare domain and PC conflicts** — unattested COIs
      are a listed desk-rejection trigger.
- [ ] Submit the abstract by 09-25, then the PDF by 10-01.
- [ ] Decide whether to use an institutional email address.
- [ ] Confirm the Jecheon campus city if it needs correcting.
- [ ] **Supply authors for two citations we could not verify.** `amemguard` and
      `memincept` are cited from OpenReview forum IDs, and OpenReview blocks
      automated access (HTTP 403, challenge required), so their author lists and
      exact titles are unconfirmed and they render without authors. Every other
      citation was checked against its primary source. Open
      <https://openreview.net/forum?id=udqe7UZUZ6> and
      <https://openreview.net/forum?id=1YNrlSSRsk> in a browser and fill in
      `paper/refs.bib`, or drop the two references.

## Desk-rejection triggers, checked

The CFP names four: incomplete abstract, unattested COIs, violated formatting,
exceeded caps. The two we control are verified:

| Check | Status |
|---|---|
| Page cap, 12 excluding references | **8 pages**, references begin on page 8 |
| Official template | `acmart` v2.19 `[sigconf, nonacm]` + vendored `pvldb.sty` |
| Category tag in the PDF title | present |
| Author names on page 1 (single-blind) | present |
| PVLDB reference-format / CC / ISSN / availability blocks | all four render |
| Build | 0 errors, 0 undefined references or citations |
| Fonts | all embedded, no Type 3 |
| Figure alt text | `\Description` on all three figures |
| Bibliography | authors verified against primary sources, except the two above |

## Artifact, verified from a clean clone

Run on a fresh clone with a fresh interpreter, which is how the Reproducibility
Committee will see it — not from the development environment, where three
failures were invisible:

```
temvera verify-artifacts …      30 sealed runs valid
verify_paper_claims.py          87 printed figures match their runs
pytest                          130 passed, 5 skipped
ruff check .                    passed (on a newer ruff than we develop against)
```

The five skips are the tests that check documentation quotes against mem0 and
graphiti-core, which are not dependencies; they run only where those packages
are installed.

**Requires CPython 3.11+.** On 3.10 pip backtracks for fifteen minutes before
reporting it, so both README and REPRODUCING put that check first.

## What regenerating the runs needs

An OpenAI key, a Neo4j 5.26 server, and a second interpreter for LangMem, whose
`openai` requirement conflicts with the pinned Mem0 and Graphiti. Scoring and
aggregation need none of these — that separation is deliberate and is the claim
the committee can check cheaply.
