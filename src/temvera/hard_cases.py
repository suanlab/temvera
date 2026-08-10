"""Hand-inspectable retrieval cases designed to avoid aggregate saturation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .hybrid import HardRetrievalCase
from .model import Authority, Belief


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def hard_retrieval_fixture(
    variant: int = 0,
) -> tuple[tuple[Belief, ...], tuple[HardRetrievalCase, ...]]:
    suffix = "" if variant == 0 else f"-v{variant}"
    semantic_pairs = (
        ("automobile", "car"),
        ("dwelling", "home"),
        ("physician", "doctor"),
    )
    semantic_value, semantic_query = semantic_pairs[variant % len(semantic_pairs)]
    ids = {
        name: f"{base}{suffix}"
        for name, base in {
            "exact": "z-exact",
            "lexical": "z-lexical",
            "vector": "z-vector",
            "temporal_stale": "a-temporal-stale",
            "temporal_current": "z-temporal-current",
            "graph_seed": "a-graph-seed",
            "graph_target": "z-graph-target",
        }.items()
    }
    code = f"casecode-{91827 + variant}"
    marker = f"markergraph{variant}"
    beliefs = (
        _belief(ids["exact"], f"acct-alpha-{variant}", "owner", "Mina"),
        _belief(ids["lexical"], "ticket", "reference", code),
        _belief(ids["vector"], "transport", "preference", semantic_value),
        _belief(
            ids["temporal_stale"],
            "user",
            "city",
            "Seoul",
            valid_to=NOW - timedelta(days=1),
            superseded_by=ids["temporal_current"],
        ),
        _belief(
            ids["temporal_current"],
            "user",
            "city",
            "Busan",
            valid_from=NOW - timedelta(days=1),
        ),
        _belief(ids["graph_seed"], "report", "finding", marker),
        _belief(
            ids["graph_target"],
            "risk",
            "action",
            "review",
            derived_from=(ids["graph_seed"],),
        ),
        *tuple(
            _belief(
                f"a-distractor-{index}{suffix}",
                "noise",
                "item",
                f"filler-{index}-{variant}",
            )
            for index in range(8)
        ),
    )
    cases = (
        HardRetrievalCase(
            "exact_identifier",
            f"acct-alpha-{variant}",
            "owner",
            "who is responsible",
            NOW,
            frozenset({ids["exact"]}),
            1,
        ),
        HardRetrievalCase(
            "lexical_code",
            "unknown",
            "unknown",
            code,
            NOW,
            frozenset({ids["lexical"]}),
            1,
        ),
        HardRetrievalCase(
            "vector_synonym",
            "unknown",
            "unknown",
            semantic_query,
            NOW,
            frozenset({ids["vector"]}),
            1,
        ),
        HardRetrievalCase(
            "temporal_version",
            "user",
            "city",
            "user city",
            NOW,
            frozenset({ids["temporal_current"]}),
            1,
        ),
        HardRetrievalCase(
            "graph_derivation",
            "report",
            "finding",
            marker,
            NOW,
            frozenset({ids["graph_target"]}),
            2,
        ),
    )
    return beliefs, cases


def _belief(
    belief_id: str,
    subject: str,
    attribute: str,
    value: str,
    *,
    valid_from: datetime = NOW - timedelta(days=30),
    valid_to: datetime | None = None,
    superseded_by: str | None = None,
    derived_from: tuple[str, ...] = (),
) -> Belief:
    return Belief(
        belief_id=belief_id,
        subject=subject,
        attribute=attribute,
        value=value,
        valid_from=valid_from,
        valid_to=valid_to,
        recorded_at=valid_from,
        last_confirmed_at=valid_from,
        authority=Authority.VERIFIED_TOOL,
        sources=(f"fixture:{belief_id}",),
        derived_from=derived_from,
        superseded_by=superseded_by,
    )
