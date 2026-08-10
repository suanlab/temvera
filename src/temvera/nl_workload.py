"""Natural-language rendering of lifecycle histories for external systems.

The renderer turns a typed :class:`~temvera.model.MemoryEvent` history into
deterministic conversational turns and natural-language queries, while keeping
the ground-truth answer separate (computed by the oracle). This lets opaque
external memory systems (which only ingest text) be scored against the same
bitemporal truth as the internal baselines, and removes the "BM25 receives
structured query terms" external-validity gap (E-043).

Rendering is a pure function of the event history: identical inputs produce
byte-identical turns and cases.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .evaluation import QueryCase, cases_from_oracle
from .model import MemoryEvent, Operation

# Distinct, embedding-separable surface names. The synthetic generator emits
# near-identical tokens ("entity-000", "place-38") that collapse under a
# semantic embedder, confounding a bitemporal comparison with an inability to
# tell identifiers apart. `naturalize_events` relabels them via an injective
# map so external LLM/embedding systems are tested on temporal semantics, not
# tokenization. The relabeling is a pure bijection: it leaves the oracle's
# bitemporal logic and every baseline's ranking structurally identical.
_PERSONS = (
    "Mina", "Noah", "Sora", "Liam", "Yuna", "Omar", "Priya", "Kenji",
    "Aisha", "Diego", "Lena", "Tariq", "Freya", "Hugo", "Zara", "Ivan",
    "Maya", "Sven", "Nadia", "Pablo", "Ravi", "Elsa", "Kwame", "Bianca",
    "Toma", "Greta", "Idris", "Wei", "Rosa", "Andre", "Suki", "Bruno",
    "Leyla", "Milo", "Farah", "Otto", "Ines", "Cyrus", "Dalia", "Emre",
)
_CITIES = (
    "Seoul", "Cairo", "Oslo", "Lima", "Accra", "Porto", "Riga", "Perth",
    "Quito", "Nantes", "Cebu", "Split", "Kobe", "Bergen", "Ghent", "Pune",
    "Davao", "Aarhus", "Cuenca", "Turku", "Nagoya", "Leon", "Kumasi", "Bari",
    "Utrecht", "Galway", "Tabriz", "Xian", "Recife", "Nice", "Sapporo", "Graz",
    "Izmir", "Malmo", "Fez", "Linz", "Vigo", "Shiraz", "Bursa", "Trier",
    "Mendoza", "Cork", "Mersin", "Wuxi", "Natal", "Lyon", "Sendai", "Basel",
    "Konya", "Zagreb", "Aba", "Delft", "Almaty", "Faro", "Hue", "Jinan",
    "Ordu", "Breda", "Enugu", "Leiden",
)


def _pick(pool: tuple[str, ...], index: int, kind: str) -> str:
    return pool[index] if index < len(pool) else f"{kind}-{index}"


def naturalize_events(events: tuple[MemoryEvent, ...]) -> tuple[MemoryEvent, ...]:
    """Relabel synthetic subjects/attributes/values to distinct natural names.

    Injective over the distinct tokens actually present, so no two originals
    collapse to one name. Belief and event identifiers are unchanged.
    """
    subjects = sorted({e.subject for e in events if e.subject})
    values = sorted({e.value for e in events if e.value})
    subject_map = {name: _pick(_PERSONS, i, "Person") for i, name in enumerate(subjects)}
    value_map = {name: _pick(_CITIES, i, "City") for i, name in enumerate(values)}
    out: list[MemoryEvent] = []
    for event in events:
        out.append(
            replace(
                event,
                subject=subject_map.get(event.subject, event.subject)
                if event.subject
                else event.subject,
                value=value_map.get(event.value, event.value)
                if event.value
                else event.value,
                attribute="home city"
                if event.attribute == "location"
                else event.attribute,
            )
        )
    return tuple(out)


@dataclass(frozen=True, slots=True)
class WorkloadTurn:
    """One natural-language statement derived from a single lifecycle event."""

    recorded_at: datetime
    text: str
    event_id: str


@dataclass(frozen=True, slots=True)
class NLQueryCase:
    """A natural-language query paired with value-level ground truth.

    External systems answer in free text, so truth is expressed as the set of
    belief *values* that a correct answer must contain (``expected_values``) and
    the superseded/deleted values a correct answer must avoid (``stale_values``).
    This mirrors ForgetEval's deterministic substring scoring (E-013).
    """

    case_id: str
    query_text: str
    subject: str
    attribute: str
    valid_at: datetime
    transaction_at: datetime
    expected_values: frozenset[str]
    stale_values: frozenset[str]
    category: str


def _ingest_by_belief(events: tuple[MemoryEvent, ...]) -> dict[str, MemoryEvent]:
    return {
        event.belief_id: event
        for event in events
        if event.operation is Operation.INGEST
    }


def _day(moment: datetime) -> str:
    return moment.date().isoformat()


def render_turns(events: tuple[MemoryEvent, ...]) -> tuple[WorkloadTurn, ...]:
    """Render each event as one deterministic natural-language turn."""
    ingests = _ingest_by_belief(events)
    turns: list[WorkloadTurn] = []
    for event in events:
        ingest = ingests.get(event.belief_id)
        subject = event.subject or (ingest.subject if ingest else event.belief_id)
        attribute = event.attribute or (ingest.attribute if ingest else "value")
        value = event.value or (ingest.value if ingest else "")
        if event.operation is Operation.INGEST:
            text = (
                f"[recorded {_day(event.recorded_at)}] {subject}'s {attribute} "
                f"is {value}, valid from {_day(event.valid_from)}."
            )
        elif event.operation is Operation.RECONFIRM:
            text = (
                f"[recorded {_day(event.recorded_at)}] Confirmed that {subject}'s "
                f"{attribute} is still {value}."
            )
        elif event.operation is Operation.SUPERSEDE:
            valid_from = event.valid_from or event.recorded_at
            text = (
                f"[recorded {_day(event.recorded_at)}] Update: {subject}'s "
                f"{attribute} is now {value} as of {_day(valid_from)}, "
                f"replacing the previous value."
            )
        elif event.operation is Operation.EXPIRE:
            boundary = event.valid_to or event.valid_from or event.recorded_at
            text = (
                f"[recorded {_day(event.recorded_at)}] {subject}'s {attribute} "
                f"({value}) is no longer valid after {_day(boundary)}."
            )
        elif event.operation is Operation.PURGE:
            text = (
                f"[recorded {_day(event.recorded_at)}] Permanently delete the "
                f"record that {subject}'s {attribute} was {value}."
            )
        else:  # pragma: no cover - Operation is exhaustive
            raise ValueError(f"unhandled operation: {event.operation}")
        turns.append(
            WorkloadTurn(
                recorded_at=event.recorded_at, text=text, event_id=event.event_id
            )
        )
    return tuple(turns)


def render_query(case: QueryCase) -> str:
    """Render a bitemporal query case as a natural-language question."""
    return (
        f"What is {case.subject}'s {case.attribute} as of {_day(case.valid_at)}, "
        f"based only on what was known by {_day(case.transaction_at)}?"
    )


def build_nl_cases(events: tuple[MemoryEvent, ...]) -> tuple[NLQueryCase, ...]:
    """Resolve oracle query cases into value-level natural-language cases."""
    ingests = _ingest_by_belief(events)

    def value_of(belief_id: str) -> str | None:
        event = ingests.get(belief_id)
        return event.value if event else None

    def values(ids: frozenset[str]) -> frozenset[str]:
        return frozenset(
            value for value in (value_of(belief_id) for belief_id in ids) if value
        )

    cases: list[NLQueryCase] = []
    for case in cases_from_oracle(events):
        cases.append(
            NLQueryCase(
                case_id=case.case_id,
                query_text=render_query(case),
                subject=case.subject,
                attribute=case.attribute,
                valid_at=case.valid_at,
                transaction_at=case.transaction_at,
                expected_values=values(case.expected_ids),
                stale_values=values(case.stale_ids) - values(case.expected_ids),
                category=case.category,
            )
        )
    return tuple(cases)
