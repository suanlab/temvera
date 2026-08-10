"""Deterministic lifecycle baselines and operation-level metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math
import re
from typing import Protocol

from .model import Belief, MemoryEvent, Operation
from .oracle import LifecycleOracle


class QuerySystem(Protocol):
    def query(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        transaction_at: datetime,
    ) -> tuple[Belief, ...]: ...


class AppendOnlyBaseline(LifecycleOracle):
    """Ignore revision, expiry, and purge operations."""

    def __init__(self, events: tuple[MemoryEvent, ...]) -> None:
        super().__init__(e for e in events if e.operation is Operation.INGEST)


class FullContextBaseline(AppendOnlyBaseline):
    """Expose every recorded fact available at the query transaction time."""


class RecentContextBaseline(AppendOnlyBaseline):
    """Return the most recently recorded raw fact for a subject and attribute."""

    def query(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        transaction_at: datetime,
    ) -> tuple[Belief, ...]:
        del valid_at
        matching = [
            belief
            for belief in self.state_as_of(transaction_at).values()
            if belief.subject == subject and belief.attribute == attribute
        ]
        return tuple(sorted(matching, key=lambda item: item.recorded_at, reverse=True)[:1])


class BM25Baseline(AppendOnlyBaseline):
    """Dependency-free full-text retrieval over raw facts with a fixed budget."""

    def __init__(self, events: tuple[MemoryEvent, ...], *, limit: int = 1) -> None:
        if limit < 1:
            raise ValueError("limit must be positive")
        super().__init__(events)
        self.limit = limit

    def query(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        transaction_at: datetime,
    ) -> tuple[Belief, ...]:
        del valid_at
        beliefs = tuple(self.state_as_of(transaction_at).values())
        if not beliefs:
            return ()
        query_terms = _tokens(f"{subject} {attribute}")
        documents = tuple(_tokens(f"{b.subject} {b.attribute} {b.value}") for b in beliefs)
        average_length = sum(map(len, documents)) / len(documents)
        document_frequency = {
            term: sum(term in document for document in documents) for term in query_terms
        }
        ranked = sorted(
            zip(beliefs, documents, strict=True),
            key=lambda pair: (
                _bm25_score(
                    pair[1], query_terms, document_frequency, len(documents), average_length
                ),
                pair[0].recorded_at,
                pair[0].belief_id,
            ),
            reverse=True,
        )
        return tuple(belief for belief, _ in ranked[: self.limit])


class LastWriteWinsBaseline(LifecycleOracle):
    """Return only the latest recorded matching belief, ignoring valid time."""

    def query(
        self,
        subject: str,
        attribute: str,
        *,
        valid_at: datetime,
        transaction_at: datetime,
    ) -> tuple[Belief, ...]:
        del valid_at
        matching = [
            belief
            for belief in self.state_as_of(transaction_at).values()
            if belief.subject == subject and belief.attribute == attribute
        ]
        return tuple(sorted(matching, key=lambda b: b.recorded_at, reverse=True)[:1])


@dataclass(frozen=True, slots=True)
class QueryCase:
    case_id: str
    subject: str
    attribute: str
    valid_at: datetime
    transaction_at: datetime
    expected_ids: frozenset[str]
    stale_ids: frozenset[str] = frozenset()
    category: str = "unspecified"


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    cases: int
    exact_state_accuracy: float
    evidence_recall: float
    stale_use_rate: float


@dataclass(frozen=True, slots=True)
class CaseError:
    case_id: str
    missed_ids: tuple[str, ...]
    stale_ids: tuple[str, ...]
    unexpected_ids: tuple[str, ...]


def evaluate(system: QuerySystem, cases: tuple[QueryCase, ...]) -> EvaluationResult:
    if not cases:
        raise ValueError("at least one query case is required")
    exact = 0
    recall_total = 0.0
    stale_selected = 0
    selected_total = 0
    for case in cases:
        returned = system.query(
            case.subject,
            case.attribute,
            valid_at=case.valid_at,
            transaction_at=case.transaction_at,
        )
        returned_ids = {belief.belief_id for belief in returned}
        exact += returned_ids == set(case.expected_ids)
        recall_total += (
            len(returned_ids.intersection(case.expected_ids)) / len(case.expected_ids)
            if case.expected_ids
            else float(not returned_ids)
        )
        stale_selected += len(returned_ids.intersection(case.stale_ids))
        selected_total += len(returned_ids)
    return EvaluationResult(
        cases=len(cases),
        exact_state_accuracy=exact / len(cases),
        evidence_recall=recall_total / len(cases),
        stale_use_rate=stale_selected / selected_total if selected_total else 0.0,
    )


def error_analysis(
    system: QuerySystem, cases: tuple[QueryCase, ...]
) -> tuple[CaseError, ...]:
    """Return exact per-case failure attribution for lifecycle metrics."""
    errors: list[CaseError] = []
    for case in cases:
        returned = system.query(
            case.subject,
            case.attribute,
            valid_at=case.valid_at,
            transaction_at=case.transaction_at,
        )
        returned_ids = {belief.belief_id for belief in returned}
        expected_ids = set(case.expected_ids)
        missed_ids = tuple(sorted(expected_ids - returned_ids))
        unexpected_ids = tuple(sorted(returned_ids - expected_ids))
        stale_ids = tuple(sorted(returned_ids.intersection(case.stale_ids)))
        if missed_ids or unexpected_ids:
            errors.append(
                CaseError(
                    case_id=case.case_id,
                    missed_ids=missed_ids,
                    stale_ids=stale_ids,
                    unexpected_ids=unexpected_ids,
                )
            )
    return tuple(errors)


def cases_from_oracle(events: tuple[MemoryEvent, ...]) -> tuple[QueryCase, ...]:
    """Build valid-time and transaction-time cases, including deleted state."""
    if not events:
        return ()
    oracle = LifecycleOracle(events)
    transaction_at = max(event.recorded_at for event in events)
    ingests = tuple(event for event in events if event.operation is Operation.INGEST)
    by_id = {event.belief_id: event for event in ingests}
    purges = tuple(event for event in events if event.operation is Operation.PURGE)
    expiries = tuple(event for event in events if event.operation is Operation.EXPIRE)
    specifications: set[tuple[str, str, datetime, datetime]] = set()
    for event in ingests:
        assert event.subject is not None
        assert event.attribute is not None
        assert event.valid_from is not None
        specifications.add(
            (event.subject, event.attribute, event.valid_from, transaction_at)
        )
        specifications.add(
            (event.subject, event.attribute, event.valid_from, event.recorded_at)
        )
    for event in events:
        if event.operation is not Operation.EXPIRE:
            continue
        target = by_id[event.belief_id]
        assert target.subject is not None
        assert target.attribute is not None
        boundary = event.valid_to or event.valid_from or event.recorded_at
        specifications.add((target.subject, target.attribute, boundary, transaction_at))
        specifications.add((target.subject, target.attribute, boundary, event.recorded_at))
    cases: list[QueryCase] = []
    for index, (subject, attribute, valid_at, known_at) in enumerate(
        sorted(specifications)
    ):
        expected = oracle.query(
            subject,
            attribute,
            valid_at=valid_at,
            transaction_at=known_at,
        )
        expected_ids = frozenset(item.belief_id for item in expected)
        candidate_ids = {
            event.belief_id
            for event in ingests
            if event.subject == subject
            and event.attribute == attribute
            and event.recorded_at <= known_at
        }
        if any(
            event.belief_id in candidate_ids and event.recorded_at <= known_at
            for event in purges
        ):
            category = "purge"
        elif any(
            event.belief_id in candidate_ids
            and event.recorded_at <= known_at
            and (event.valid_to or event.valid_from or event.recorded_at) == valid_at
            for event in expiries
        ):
            category = "expiry_boundary"
        elif known_at < transaction_at:
            category = "transaction_as_of"
        else:
            category = "valid_time"
        cases.append(
            QueryCase(
                case_id=f"case-{index:06d}",
                subject=subject,
                attribute=attribute,
                valid_at=valid_at,
                transaction_at=known_at,
                expected_ids=expected_ids,
                stale_ids=frozenset(candidate_ids - set(expected_ids)),
                category=category,
            )
        )
    return tuple(cases)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(re.findall(r"[a-z0-9]+", text.casefold()))


def _bm25_score(
    document: tuple[str, ...],
    query: tuple[str, ...],
    document_frequency: dict[str, int],
    document_count: int,
    average_length: float,
) -> float:
    k1 = 1.2
    b = 0.75
    score = 0.0
    for term in set(query):
        frequency = document.count(term)
        if not frequency:
            continue
        inverse_frequency = math.log(
            1 + (document_count - document_frequency[term] + 0.5)
            / (document_frequency[term] + 0.5)
        )
        denominator = frequency + k1 * (
            1 - b + b * len(document) / average_length
        )
        score += inverse_frequency * frequency * (k1 + 1) / denominator
    return score
