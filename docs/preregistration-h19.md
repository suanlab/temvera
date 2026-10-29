# Preregistration: a temporal positive control (H19)

Committed and pushed before `scripts/positive_control_runs.py` has run on the
paper's workloads. Results are reported whatever they are. Responds to the
pre-submission audit (`CHECK.md`, G8 and Reviewer A): the paper has no system
that applies both time axes, so it cannot show that the input supports correct
answers or that the harness credits a store that does.

## Design

`temvera.positive_control.PositiveControl` reads each rendered turn -- the text
every system receives, not the events -- into a row with a valid-time interval
and a recording time, using the renderer's sentence patterns, and answers each
question with a valid-time and a transaction-time predicate: the value valid at
the asked date among statements recorded by the asked knowledge date, with
corrections overriding their interval, expiries ending a value at the start of
their day, and a deletion request removing everything about the attribute. No
LLM. It was developed only on histories with seeds 1001-1005 (main-grid
profiles and scales) and 1001-1010 (the correction profile), none of which the
paper uses, and frozen before this file was written: there it answered 494 of
503 grid questions (the 9 misses are purge questions under the generator's
original scope, which the request's own scope credits) and all 512 correction
questions.

Runs: `positive-control-grid-v1` (the cells of `external-mem0-grid-v2`,
forward-checkpoint replay) and `positive-control-final-store-v1` (the cells of
`final-store-corrections-hindsight-reflect-v1`, whole history in one pass).
Scored by the grid's scorer; purge under both scopes. It is a control fitted to
our renderer, not a system to rank against the others.

Analysis: `scripts/analyze_h19.py`, committed with this file.

## Predictions

- **H19a -- the input supports every answer:** on the 20 matched main-grid
  cells, under the request's scope, the control answers all 484 questions
  exactly.
- **H19b -- the purge scope is the only gap:** under the generator's original
  purge scope it answers exactly 455 of 484, the 29 misses being the purge
  questions that expect a value the request asked to delete.
- **H19c -- the final store can say what it knew:** on the H11 correction
  histories asked in one pass, it answers all 45 questions about what was known
  before a correction under the strict count, and every other question exactly.
- **H19d -- nothing is skipped:** every rendered turn is parsed.

## Outcomes (recorded 2026-10-29 KST; `scripts/analyze_h19.py`)

| Prediction | Outcome |
|---|---|
| H19a: 484/484 on the main grid under the request's scope | **holds** -- 484/484 |
| H19b: 455/484 under the original purge scope | **holds** -- 455/484 |
| H19c: 45/45 knew-then questions from the final store, all others exact | **holds** -- 45/45 strict; 513/513 questions |
| H19d: every turn parsed | **holds** -- 0 unparsed |

The rendered text supports every answer the oracle expects, and the harness and
scorer credit a store that applies both time axes. The control is fitted to our
renderer's sentence patterns; it shows what the input allows, not what a
deployed system could be expected to reach.
