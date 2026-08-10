"""Development-only channel-weight calibration and held-out evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from .hard_cases import hard_retrieval_fixture
from .hybrid import HybridRetriever
from .index import weighted_reciprocal_rank_fusion


FUSION_CHANNELS = ("exact", "lexical", "vector", "graph")


@dataclass(frozen=True, slots=True)
class FusionExample:
    rankings: dict[str, tuple[str, ...]]
    expected_ids: frozenset[str]
    eligible_ids: frozenset[str]
    limit: int


@dataclass(frozen=True, slots=True)
class FusionComparison:
    development_examples: int
    test_examples: int
    learned_weights: tuple[tuple[str, float], ...]
    fixed_test_recall_at_budget: float
    calibrated_test_recall_at_budget: float


def build_fusion_examples(variants: tuple[int, ...]) -> tuple[FusionExample, ...]:
    examples = []
    for variant in variants:
        beliefs, cases = hard_retrieval_fixture(variant)
        retriever = HybridRetriever(beliefs)
        for case in cases:
            if case.category == "temporal_version":
                continue
            examples.append(
                FusionExample(
                    rankings=retriever.rankings(
                        case.subject,
                        case.attribute,
                        valid_at=case.valid_at,
                        query_text=case.query_text,
                        limit=case.limit,
                    ),
                    expected_ids=case.expected_ids,
                    eligible_ids=frozenset(
                        belief.belief_id
                        for belief in beliefs
                        if belief.valid_at(case.valid_at)
                    ),
                    limit=case.limit,
                )
            )
    return tuple(examples)


def calibrate_fusion(
    examples: tuple[FusionExample, ...],
    *,
    grid: tuple[float, ...] = (0.0, 0.5, 1.0, 2.0),
) -> dict[str, float]:
    if not examples:
        raise ValueError("development examples are required")
    best_score = -1.0
    best: tuple[float, ...] | None = None
    for values in product(grid, repeat=len(FUSION_CHANNELS)):
        if not any(values):
            continue
        weights = dict(zip(FUSION_CHANNELS, values))
        score = fusion_recall_at_1(examples, weights)
        if score > best_score or (score == best_score and (best is None or values < best)):
            best_score = score
            best = values
    assert best is not None
    return dict(zip(FUSION_CHANNELS, best))


def fusion_recall_at_1(
    examples: tuple[FusionExample, ...], weights: dict[str, float]
) -> float:
    recalled = 0
    for example in examples:
        fused = weighted_reciprocal_rank_fusion(example.rankings, weights)
        selected = [
            belief_id
            for belief_id, _ in fused
            if belief_id in example.eligible_ids
        ][: example.limit]
        recalled += bool(set(selected) & example.expected_ids)
    return recalled / len(examples)


def compare_fusion(
    development_variants: tuple[int, ...], test_variants: tuple[int, ...]
) -> FusionComparison:
    if set(development_variants) & set(test_variants):
        raise ValueError("development and test variants must be disjoint")
    development = build_fusion_examples(development_variants)
    test = build_fusion_examples(test_variants)
    learned = calibrate_fusion(development)
    fixed = {channel: 1.0 for channel in FUSION_CHANNELS}
    return FusionComparison(
        development_examples=len(development),
        test_examples=len(test),
        learned_weights=tuple(sorted(learned.items())),
        fixed_test_recall_at_budget=fusion_recall_at_1(test, fixed),
        calibrated_test_recall_at_budget=fusion_recall_at_1(test, learned),
    )
