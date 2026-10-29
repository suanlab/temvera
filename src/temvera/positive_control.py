"""A temporal positive control: bitemporal predicates over the rendered text.

Every system in the paper receives the same rendered turns and is asked the
same questions. This control does what none of them does: it reads each turn
into a row with a valid-time interval and a recording time, and answers each
question with a valid-time and a transaction-time predicate. It knows nothing
the turns do not say -- it parses the text, not the events -- so it shows what
the input supports and that the harness and scorer credit a store that applies
both axes. It is fitted to our renderer's sentence patterns, so it is a
control on this workload, not a system to compare with the others.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from .external_harness import NLQueryCase
from .nl_workload import PURGE_WORDINGS, WorkloadTurn

_DAY = r"(\d{4}-\d{2}-\d{2})"
_HEAD = re.compile(r"^\[recorded " + _DAY + r"\] (.*)$", re.S)
_INGEST = re.compile(r"^(.+?)'s (.+?) is (.+?), valid from " + _DAY + r"\.$")
_UPDATE = re.compile(r"^Update: (.+?)'s (.+?) is now (.+?) as of " + _DAY + r", replacing the previous value\.$")
_CLOSED = re.compile(r"^(.+?)'s (.+?) was (.+?) from " + _DAY + r" until " + _DAY + r"\.$")
_CORRECTION = re.compile(r"^Correction: (.+?)'s (.+?) from " + _DAY + r" until " + _DAY
                         + r" was actually (.+?), not (.+?)\.$")
_EXPIRE = re.compile(r"^(.+?)'s (.+?) \((.+?)\) is no longer valid after " + _DAY + r"\.$")
_CONFIRM = re.compile(r"^Confirmed that (.+?)'s (.+?) is still (.+?)\.$")
_QUERY = re.compile(r"^What is (.+?)'s (.+?) as of " + _DAY + r", based only on what was known by "
                    + _DAY + r"\?$")
_PURGES = [re.compile("^" + re.escape(w).replace(r"\{subject\}", "(.+?)").replace(r"\{attribute\}", "(.+?)") + "$")
           for w in PURGE_WORDINGS]


@dataclass(frozen=True, slots=True)
class Row:
    subject: str
    attribute: str
    value: str
    valid_from: date
    valid_to: date | None  # exclusive
    recorded: date
    kind: str  # "assert", "correct", "expire", "purge"


class PositiveControl:
    """The control as a ``MemorySystem``: ``reset``, ``ingest``, ``answer``."""

    def __init__(self) -> None:
        self.rows: list[Row] = []
        self.unparsed: list[str] = []

    def reset(self) -> None:
        self.rows = []

    def ingest(self, turn: WorkloadTurn) -> None:
        head = _HEAD.match(turn.text)
        if not head:
            self.unparsed.append(turn.text)
            return
        recorded, body = date.fromisoformat(head.group(1)), head.group(2)
        if m := _CORRECTION.match(body):
            s, a, start, end, value, _old = m.groups()
            self.rows.append(Row(s, a, value, date.fromisoformat(start), date.fromisoformat(end), recorded,
                                 "correct"))
        elif m := _UPDATE.match(body):
            s, a, value, start = m.groups()
            self.rows.append(Row(s, a, value, date.fromisoformat(start), None, recorded, "assert"))
        elif m := _CLOSED.match(body):
            s, a, value, start, end = m.groups()
            self.rows.append(Row(s, a, value, date.fromisoformat(start), date.fromisoformat(end), recorded,
                                 "assert"))
        elif m := _INGEST.match(body):
            s, a, value, start = m.groups()
            self.rows.append(Row(s, a, value, date.fromisoformat(start), None, recorded, "assert"))
        elif m := _EXPIRE.match(body):
            s, a, value, end = m.groups()
            self.rows.append(Row(s, a, value, date.fromisoformat(end), None, recorded, "expire"))
        elif _CONFIRM.match(body):
            return  # restates a value already held
        else:
            for pattern in _PURGES:
                if m := pattern.match(body):
                    s, a = m.groups()
                    self.rows.append(Row(s, a, "", recorded, None, recorded, "purge"))
                    return
            self.unparsed.append(turn.text)

    def value_at(self, subject: str, attribute: str, valid_at: date, known_by: date) -> str | None:
        """The value valid at ``valid_at`` on what was recorded by ``known_by``."""
        rows = [r for r in self.rows if r.subject == subject and r.attribute == attribute
                and r.recorded <= known_by]
        if any(r.kind == "purge" for r in rows):
            return None  # the request asks for everything about the attribute to go
        for r in sorted((r for r in rows if r.kind == "correct"), key=lambda r: r.recorded, reverse=True):
            if r.valid_from <= valid_at < r.valid_to:
                return r.value
        asserted = sorted((r for r in rows if r.kind == "assert"), key=lambda r: (r.valid_from, r.recorded))
        current = None
        for r in asserted:
            if r.valid_from <= valid_at and (r.valid_to is None or valid_at < r.valid_to):
                current = r
        if current is None:
            return None
        for r in rows:
            # "no longer valid after D" is the renderer's wording for an interval
            # that ends at the start of D (the event's valid_to is D 00:00), so
            # the value is gone on D itself.
            if r.kind == "expire" and r.value == current.value and valid_at >= r.valid_from:
                return None
        return current.value

    def answer(self, case: NLQueryCase) -> str:
        m = _QUERY.match(case.query_text)
        if not m:
            return "UNKNOWN"
        subject, attribute, valid_at, known_by = m.groups()
        value = self.value_at(subject, attribute, date.fromisoformat(valid_at), date.fromisoformat(known_by))
        return value if value is not None else "UNKNOWN"
