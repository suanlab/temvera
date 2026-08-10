"""Context-budget and local retrieval latency measurements."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter_ns

from .hybrid import CHANNELS, HardRetrievalCase, HybridRetriever


@dataclass(frozen=True, slots=True)
class EfficiencyRow:
    budget_items: int
    cases: int
    channels: tuple[str, ...]
    context_tokens_approx: float
    evidence_recall: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    samples: int


def benchmark_efficiency(
    retriever: HybridRetriever,
    cases: tuple[HardRetrievalCase, ...],
    *,
    budgets: tuple[int, ...],
    repeats: int,
    channels: tuple[str, ...] = CHANNELS,
) -> tuple[EfficiencyRow, ...]:
    if not cases or not budgets or repeats < 1:
        raise ValueError("cases, budgets, and positive repeats are required")
    rows = []
    for budget in sorted(set(budgets)):
        if budget < 1:
            raise ValueError("budgets must be positive")
        samples: list[int] = []
        recalled = 0
        tokens = 0
        for case in cases:
            first = retriever.retrieve(
                case.subject,
                case.attribute,
                valid_at=case.valid_at,
                query_text=case.query_text,
                channels=channels,
                limit=budget,
            )
            recalled += bool({item.belief_id for item in first} & case.expected_ids)
            tokens += sum(_approx_tokens(item.value) for item in first)
            for _ in range(repeats):
                started = perf_counter_ns()
                retriever.retrieve(
                    case.subject,
                    case.attribute,
                    valid_at=case.valid_at,
                    query_text=case.query_text,
                    channels=channels,
                    limit=budget,
                )
                samples.append(perf_counter_ns() - started)
        samples.sort()
        rows.append(
            EfficiencyRow(
                budget_items=budget,
                cases=len(cases),
                channels=channels,
                context_tokens_approx=tokens / len(cases),
                evidence_recall=recalled / len(cases),
                latency_p50_ms=_percentile(samples, 0.50) / 1_000_000,
                latency_p95_ms=_percentile(samples, 0.95) / 1_000_000,
                latency_p99_ms=_percentile(samples, 0.99) / 1_000_000,
                samples=len(samples),
            )
        )
    return tuple(rows)


def _percentile(sorted_values: list[int], quantile: float) -> int:
    index = round((len(sorted_values) - 1) * quantile)
    return sorted_values[index]


def _approx_tokens(text: str) -> int:
    return max(1, (len(text.encode("utf-8")) + 3) // 4)
