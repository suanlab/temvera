# Human Audit Study Protocol

> Scope decision D-009: this protocol is the approved deliverable. No
> participants are recruited and no human-effectiveness result is claimed.

## Objective and preregistered hypothesis

The study tests whether a provenance-linked event diff improves planted-fault
detection and correction over an opaque current-state view. The primary
hypothesis is higher fault-detection accuracy at equal task time. Secondary
outcomes are correction accuracy, elapsed seconds, and unintended edits. No
superiority claim is permitted before participant data and uncertainty
estimates exist.

## Design

Use a randomized within-participant crossover. Each participant receives equal
numbers of `provenance_diff` and `opaque_current_state` tasks; condition order
alternates by participant and task. `generate_audit_tasks` freezes synthetic
stale-value, wrong-subject, and missing-provenance faults from a recorded seed.
The task answer key is hidden until submission. A pilot may validate wording
but may not enter the confirmatory dataset.

The target sample size must be selected by an a priori power analysis after a
pilot variance estimate. Until then, sample size is deliberately unspecified.
Analyze binary detection/correction with a participant- and task-aware model or
paired bootstrap; report effect sizes and 95% intervals. Analyze time only for
completed tasks and report exclusions.

## Data minimization and consent

Obtain ethics review or a documented exemption before recruitment. Collect a
random participant code, condition, task ID, answer, edited-field identifiers,
and elapsed time. Do not collect names, private conversations, free-form
biographical data, keystrokes, or screen recordings. Consent must state the
purpose, duration, compensation, withdrawal procedure, retention period, and
publication of aggregate results. Store the code-to-contact mapping outside
the repository and delete it after compensation and withdrawal windows close.

## Integrity and stopping rules

Freeze tasks, assignment code, hypotheses, exclusions, and analysis before the
confirmatory run. Exclude only preregistered technical failures or withdrawn
records. Do not stop early for a favorable result. Preserve null, negative, and
contradictory outcomes. `score_audit_response` deterministically computes the
four task-level outcomes; raw participant records remain private and are never
committed.
