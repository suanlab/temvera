"""Turn LongMemEval's knowledge-update split into a bitemporal workload.

The synthetic grid gives control; it does not give realism, which is the first
thing an experiments-track reviewer will press on. LongMemEval's
``knowledge-update`` instances are the missing half: human-written conversations
in which a fact is stated, then superseded, each session carrying a real
timestamp. That is a supersession with a real valid time and a real transaction
time, and the benchmark already ships the *current* value as gold.

What it does not ship is the *superseded* value, because it never asks for one.
Recovering that is what makes an as-of query possible, and it is the one step
that cannot be done reliably by rule: the gold answer is often a paraphrase
("25 minutes and 50 seconds (or 25:50)") of what the conversation said. So this
module proposes candidates and hands them to a human, rather than guessing.
Labels are only used once confirmed.
"""

from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

_DATE = "%Y/%m/%d (%a) %H:%M"


def parse_date(text: str) -> datetime:
    return datetime.strptime(text.strip(), _DATE)


@dataclass(frozen=True, slots=True)
class Session:
    session_id: str
    recorded_at: datetime
    user_turns: tuple[str, ...]

    def sentences(self) -> tuple[str, ...]:
        out: list[str] = []
        for turn in self.user_turns:
            out += [s.strip() for s in re.split(r"(?<=[.!?])\s+", turn) if s.strip()]
        return tuple(out)


@dataclass(frozen=True, slots=True)
class UpdatePair:
    """One knowledge-update instance, reduced to its supersession."""

    question_id: str
    question: str
    asked_at: datetime
    new_value: str
    earlier: Session
    later: Session
    old_value_candidates: tuple[str, ...] = field(default_factory=tuple)

    @property
    def interval_is_ordered(self) -> bool:
        return self.earlier.recorded_at < self.later.recorded_at < self.asked_at


def _sessions(instance: dict[str, Any]) -> list[Session]:
    out = []
    for sid, date, turns in zip(
        instance["haystack_session_ids"],
        instance["haystack_dates"],
        instance["haystack_sessions"],
        strict=True,
    ):
        user = tuple(t["content"] for t in turns if t.get("role") == "user")
        out.append(Session(sid, parse_date(date), user))
    return out


def _gold_keys(gold: str) -> list[str]:
    """Tokens distinctive enough to locate the gold value in running text."""
    tokens = re.findall(r"\b[\w:/.,$-]{2,}\b", gold)
    return [t for t in tokens if any(c.isdigit() for c in t) or t[:1].isupper()]


def candidates_for(pair_sessions: tuple[Session, Session], gold: str) -> tuple[str, ...]:
    """Sentences in the earlier session most likely to carry the superseded value.

    Ranked by similarity to whichever later-session sentence states the gold, on
    the observation that a person restating an updated fact tends to reuse the
    phrasing they used the first time.
    """
    earlier, later = pair_sessions
    keys = _gold_keys(gold)
    anchors = [s for s in later.sentences() if any(k in s for k in keys)] or list(
        later.sentences()
    )
    scored: list[tuple[float, str]] = []
    for sentence in earlier.sentences():
        best = max(
            difflib.SequenceMatcher(None, anchor, sentence).ratio() for anchor in anchors
        )
        scored.append((best, sentence))
    scored.sort(reverse=True)
    return tuple(sentence for score, sentence in scored[:3] if score > 0.25)


def update_pairs(instances: Iterable[dict[str, Any]]) -> list[UpdatePair]:
    """Every knowledge-update instance whose two answer sessions are well formed."""
    pairs: list[UpdatePair] = []
    for instance in instances:
        if instance.get("question_type") != "knowledge-update":
            continue
        answer_ids = set(instance["answer_session_ids"])
        sessions = [s for s in _sessions(instance) if s.session_id in answer_ids]
        if len(sessions) != 2:
            continue
        earlier, later = sorted(sessions, key=lambda s: s.recorded_at)
        pair = UpdatePair(
            question_id=instance["question_id"],
            question=instance["question"],
            asked_at=parse_date(instance["question_date"]),
            new_value=str(instance["answer"]),
            earlier=earlier,
            later=later,
            old_value_candidates=candidates_for((earlier, later), str(instance["answer"])),
        )
        if pair.interval_is_ordered:
            pairs.append(pair)
    return pairs


def load(path: Path) -> list[UpdatePair]:
    return update_pairs(json.loads(path.read_text(encoding="utf-8")))
