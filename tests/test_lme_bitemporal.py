"""The real-data workload is derived, so the derivation is tested."""

from __future__ import annotations

from datetime import datetime

import pytest

from temvera.lme_bitemporal import Session, candidates_for, parse_date, update_pairs


def _session(sid: str, when: str, *turns: str) -> Session:
    return Session(sid, parse_date(when), turns)


def _instance(**over):
    base = {
        "question_id": "q1",
        "question_type": "knowledge-update",
        "question": "What is my best time?",
        "question_date": "2023/06/01 (Thu) 00:58",
        "answer": "25:50",
        "answer_session_ids": ["s1", "s2"],
        "haystack_session_ids": ["s0", "s1", "s2"],
        "haystack_dates": [
            "2023/05/20 (Sat) 09:00",
            "2023/05/25 (Thu) 20:21",
            "2023/05/27 (Sat) 10:20",
        ],
        "haystack_sessions": [
            [{"role": "user", "content": "Unrelated chatter about tennis."}],
            [{"role": "user", "content": "I set a personal best time of 27:12."}],
            [{"role": "user", "content": "I hope to beat my personal best of 25:50."}],
        ],
    }
    base.update(over)
    return base


def test_pair_orders_sessions_by_time_not_by_listed_order() -> None:
    reversed_dates = _instance(
        haystack_dates=[
            "2023/05/20 (Sat) 09:00",
            "2023/05/27 (Sat) 10:20",
            "2023/05/25 (Thu) 20:21",
        ]
    )
    pair = update_pairs([reversed_dates])[0]
    assert pair.earlier.recorded_at < pair.later.recorded_at


def test_only_answer_sessions_are_used() -> None:
    pair = update_pairs([_instance()])[0]
    assert {pair.earlier.session_id, pair.later.session_id} == {"s1", "s2"}


def test_instances_whose_update_postdates_the_question_are_dropped() -> None:
    """An as-of query needs the supersession to precede the question."""
    late_update = _instance(question_date="2023/05/26 (Fri) 08:00")
    assert update_pairs([late_update]) == []


def test_other_question_types_are_ignored() -> None:
    assert update_pairs([_instance(question_type="multi-session")]) == []


def test_candidate_ranks_the_sentence_that_carries_the_superseded_value() -> None:
    earlier = _session(
        "s1",
        "2023/05/25 (Thu) 20:21",
        "I set a personal best time of 27:12.",
        "The weather was cold.",
    )
    later = _session("s2", "2023/05/27 (Sat) 10:20", "I hope to beat my personal best of 25:50.")
    top = candidates_for((earlier, later), "25 minutes and 50 seconds (or 25:50)")[0]
    assert "27:12" in top


@pytest.mark.parametrize("text", ["2023/05/25 (Thu) 20:21", "2023/12/31 (Sun) 23:59"])
def test_dates_round_trip(text: str) -> None:
    assert isinstance(parse_date(text), datetime)
