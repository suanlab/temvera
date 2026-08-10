"""Controlled mechanisms for preregistered decay-placement experiments."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp, log


@dataclass(frozen=True, slots=True)
class DecayCandidate:
    belief_id: str
    semantic_score: float
    last_confirmed_at: datetime


def confidence_at(
    candidate: DecayCandidate, at: datetime, *, half_life_days: float
) -> float:
    if half_life_days <= 0:
        raise ValueError("half_life_days must be positive")
    age_days = max(0.0, (at - candidate.last_confirmed_at).total_seconds() / 86_400)
    return exp(-log(2) * age_days / half_life_days)


def rank_only_decay(
    candidates: tuple[DecayCandidate, ...],
    *,
    at: datetime,
    half_life_days: float,
    limit: int,
) -> tuple[str, ...]:
    ranked = sorted(
        candidates,
        key=lambda item: (
            -item.semantic_score
            * confidence_at(item, at, half_life_days=half_life_days),
            item.belief_id,
        ),
    )
    return tuple(item.belief_id for item in ranked[:limit])


def state_level_decay(
    candidates: tuple[DecayCandidate, ...],
    *,
    at: datetime,
    half_life_days: float,
    minimum_confidence: float,
    limit: int,
) -> tuple[str, ...]:
    eligible = (
        item
        for item in candidates
        if confidence_at(item, at, half_life_days=half_life_days)
        >= minimum_confidence
    )
    ranked = sorted(eligible, key=lambda item: (-item.semantic_score, item.belief_id))
    return tuple(item.belief_id for item in ranked[:limit])


@dataclass(frozen=True, slots=True)
class DecayCase:
    candidates: tuple[DecayCandidate, ...]
    relevant_ids: frozenset[str]
    stale_ids: frozenset[str]
    query_at: datetime


@dataclass(frozen=True, slots=True)
class DecayResult:
    cases: int
    evidence_recall_at_k: float
    stale_use_rate: float
    abstention_rate: float


@dataclass(frozen=True, slots=True)
class DecaySweepRow:
    age_days: int
    half_life_days: float
    method: str
    minimum_confidence: float
    scenario: str
    selected_ids: tuple[str, ...]
    relevant_selected: bool
    stale_selected: bool
    abstained: bool


def evaluate_decay(
    cases: tuple[DecayCase, ...],
    method: str,
    *,
    half_life_days: float,
    minimum_confidence: float = 0.25,
    limit: int = 1,
) -> DecayResult:
    if not cases:
        raise ValueError("at least one case is required")
    recalls = 0.0
    stale = 0
    selected = 0
    abstained = 0
    for case in cases:
        if method == "rank_only":
            ids = rank_only_decay(
                case.candidates,
                at=case.query_at,
                half_life_days=half_life_days,
                limit=limit,
            )
        elif method == "state_level":
            ids = state_level_decay(
                case.candidates,
                at=case.query_at,
                half_life_days=half_life_days,
                minimum_confidence=minimum_confidence,
                limit=limit,
            )
        else:
            raise ValueError(f"unknown method: {method}")
        returned = set(ids)
        recalls += (
            len(returned & case.relevant_ids) / len(case.relevant_ids)
            if case.relevant_ids
            else float(not returned)
        )
        stale += len(returned & case.stale_ids)
        selected += len(returned)
        abstained += not returned
    return DecayResult(
        cases=len(cases),
        evidence_recall_at_k=recalls / len(cases),
        stale_use_rate=stale / selected if selected else 0.0,
        abstention_rate=abstained / len(cases),
    )


def decay_smoke_cases() -> tuple[DecayCase, ...]:
    """Fixed mechanism-isolation cases; not an empirical benchmark dataset."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return (
        DecayCase(
            candidates=(
                DecayCandidate("stale-high-sim", 1.0, now - timedelta(days=180)),
                DecayCandidate("fresh-relevant", 0.7, now),
            ),
            relevant_ids=frozenset({"fresh-relevant"}),
            stale_ids=frozenset({"stale-high-sim"}),
            query_at=now,
        ),
        DecayCase(
            candidates=(
                DecayCandidate("old-relevant", 1.0, now - timedelta(days=120)),
            ),
            relevant_ids=frozenset({"old-relevant"}),
            stale_ids=frozenset(),
            query_at=now,
        ),
    )


def run_decay_sweep(
    *,
    ages_days: tuple[int, ...],
    half_lives_days: tuple[float, ...],
    thresholds: tuple[float, ...],
) -> tuple[DecaySweepRow, ...]:
    if not ages_days or not half_lives_days or not thresholds:
        raise ValueError("sweep axes must be non-empty")
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    rows: list[DecaySweepRow] = []
    for age in sorted(ages_days):
        if age < 0:
            raise ValueError("age must be non-negative")
        scenarios = {
            "changed_fact": (
                (
                    DecayCandidate("stale", 1.0, now - timedelta(days=age)),
                    DecayCandidate("relevant", 0.7, now),
                ),
                frozenset({"relevant"}),
                frozenset({"stale"}),
            ),
            "stable_old_fact": (
                (DecayCandidate("relevant", 1.0, now - timedelta(days=age)),),
                frozenset({"relevant"}),
                frozenset(),
            ),
        }
        for half_life in sorted(half_lives_days):
            for threshold in sorted(thresholds):
                for scenario, (candidates, relevant, stale) in scenarios.items():
                    rank_ids = rank_only_decay(
                        candidates, at=now, half_life_days=half_life, limit=1
                    )
                    state_ids = state_level_decay(
                        candidates,
                        at=now,
                        half_life_days=half_life,
                        minimum_confidence=threshold,
                        limit=1,
                    )
                    for method, selected_ids in (
                        ("rank_only", rank_ids),
                        ("state_level", state_ids),
                    ):
                        selected = set(selected_ids)
                        rows.append(
                            DecaySweepRow(
                                age_days=age,
                                half_life_days=half_life,
                                method=method,
                                minimum_confidence=threshold,
                                scenario=scenario,
                                selected_ids=selected_ids,
                                relevant_selected=bool(selected & relevant),
                                stale_selected=bool(selected & stale),
                                abstained=not selected,
                            )
                        )
    return tuple(rows)
