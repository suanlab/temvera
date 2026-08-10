"""Multi-seed lifecycle scaling experiment with deterministic intervals."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import random
from typing import Any

from .evaluation import (
    AppendOnlyBaseline,
    BM25Baseline,
    FullContextBaseline,
    LastWriteWinsBaseline,
    RecentContextBaseline,
    cases_from_oracle,
    evaluate,
)
from .generator import generate_histories, generate_lifecycle_suite
from .oracle import LifecycleOracle


@dataclass(frozen=True, slots=True)
class GridRow:
    seed: int
    entities: int
    revisions: int
    profile: str
    system: str
    cases: int
    exact_state_accuracy: float
    evidence_recall: float
    stale_use_rate: float


def run_lifecycle_grid(config: dict[str, Any]) -> tuple[tuple[GridRow, ...], dict[str, Any]]:
    seeds = tuple(int(value) for value in config["seeds"])
    entities_values = tuple(int(value) for value in config["entities"])
    revisions_values = tuple(int(value) for value in config["revisions"])
    bootstrap_samples = int(config.get("bootstrap_samples", 2000))
    bootstrap_seed = int(config.get("bootstrap_seed", 1729))
    profiles = tuple(
        config.get(
            "profiles",
            (
                {
                    "name": "revision_only",
                    "reconfirm_probability": 0.0,
                    "expire_probability": 0.0,
                    "purge_probability": 0.0,
                },
            ),
        )
    )
    if len(seeds) < 3:
        raise ValueError("lifecycle grid requires at least three seeds")
    if any(value < 1 for value in (*entities_values, *revisions_values)):
        raise ValueError("entities and revisions must be positive")
    if bootstrap_samples < 1:
        raise ValueError("bootstrap_samples must be positive")

    rows: list[GridRow] = []
    for profile in profiles:
        profile_name = str(profile["name"])
        for entities in entities_values:
            for revisions in revisions_values:
                for seed in seeds:
                    events = generate_histories(
                        seed=seed,
                        entities=entities,
                        revisions=revisions,
                        reconfirm_probability=float(
                            profile.get("reconfirm_probability", 0.0)
                        ),
                        expire_probability=float(
                            profile.get("expire_probability", 0.0)
                        ),
                        purge_probability=float(profile.get("purge_probability", 0.0)),
                    )
                    cases = cases_from_oracle(events)
                    systems = {
                        "oracle": LifecycleOracle(events),
                        "append_only": AppendOnlyBaseline(events),
                        "full_context": FullContextBaseline(events),
                        "recent_context": RecentContextBaseline(events),
                        "bm25_at_1": BM25Baseline(events),
                        "last_write_wins": LastWriteWinsBaseline(events),
                    }
                    for name, system in systems.items():
                        result = evaluate(system, cases)
                        rows.append(
                            GridRow(
                                seed=seed,
                                entities=entities,
                                revisions=revisions,
                                profile=profile_name,
                                system=name,
                                **asdict(result),
                            )
                        )
    summary = _summarize(
        tuple(rows), samples=bootstrap_samples, seed=bootstrap_seed
    )
    return tuple(rows), summary


def run_operation_suite(config: dict[str, Any]) -> tuple[tuple[GridRow, ...], dict[str, Any]]:
    seeds = tuple(int(value) for value in config["seeds"])
    if len(seeds) < 3:
        raise ValueError("operation suite requires at least three seeds")
    rows: list[GridRow] = []
    category_results: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for seed in seeds:
        events = generate_lifecycle_suite(seed=seed)
        cases = cases_from_oracle(events)
        systems = {
            "oracle": LifecycleOracle(events),
            "append_only": AppendOnlyBaseline(events),
            "full_context": FullContextBaseline(events),
            "recent_context": RecentContextBaseline(events),
            "bm25_at_1": BM25Baseline(events),
            "last_write_wins": LastWriteWinsBaseline(events),
        }
        for name, system in systems.items():
            result = evaluate(system, cases)
            rows.append(
                GridRow(
                    seed=seed,
                    entities=1,
                    revisions=1,
                    profile="all_operations",
                    system=name,
                    **asdict(result),
                )
            )
            for category in sorted({case.category for case in cases}):
                category_cases = tuple(
                    case for case in cases if case.category == category
                )
                category_results.setdefault(name, {}).setdefault(category, []).append(
                    asdict(evaluate(system, category_cases))
                )
    summary = _summarize(
        tuple(rows),
        samples=int(config.get("bootstrap_samples", 2000)),
        seed=int(config.get("bootstrap_seed", 1729)),
    )
    summary["by_case_category"] = {
        system: {
            category: {
                metric: sum(float(row[metric]) for row in values) / len(values)
                for metric in (
                    "exact_state_accuracy",
                    "evidence_recall",
                    "stale_use_rate",
                )
            }
            | {"cases_per_seed": values[0]["cases"], "n_seeds": len(values)}
            for category, values in categories.items()
        }
        for system, categories in category_results.items()
    }
    return tuple(rows), summary


def _summarize(
    rows: tuple[GridRow, ...], *, samples: int, seed: int
) -> dict[str, Any]:
    rng = random.Random(seed)
    result: dict[str, Any] = {
        "overall_descriptive": {},
        "by_profile_descriptive": {},
        "by_condition": {},
    }
    metrics = ("exact_state_accuracy", "evidence_recall", "stale_use_rate")
    systems = sorted({row.system for row in rows})
    for system in systems:
        selected = tuple(row for row in rows if row.system == system)
        result["overall_descriptive"][system] = {}
        for metric in metrics:
            values = tuple(float(getattr(row, metric)) for row in selected)
            result["overall_descriptive"][system][metric] = {
                "mean": sum(values) / len(values),
                "minimum": min(values),
                "maximum": max(values),
                "n_conditions_times_seeds": len(values),
            }
    for profile in sorted({row.profile for row in rows}):
        result["by_profile_descriptive"][profile] = {}
        for system in systems:
            selected = tuple(
                row for row in rows if row.system == system and row.profile == profile
            )
            result["by_profile_descriptive"][profile][system] = {}
            for metric in metrics:
                values = tuple(float(getattr(row, metric)) for row in selected)
                result["by_profile_descriptive"][profile][system][metric] = {
                    "mean": sum(values) / len(values),
                    "minimum": min(values),
                    "maximum": max(values),
                    "n_conditions_times_seeds": len(values),
                }
    conditions = sorted({(row.profile, row.entities, row.revisions) for row in rows})
    for profile, entities, revisions in conditions:
        condition_key = (
            f"profile={profile},entities={entities},revisions={revisions}"
        )
        result["by_condition"][condition_key] = {}
        for system in systems:
            selected = tuple(
                row
                for row in rows
                if row.system == system
                and row.profile == profile
                and row.entities == entities
                and row.revisions == revisions
            )
            result["by_condition"][condition_key][system] = {}
            for metric in metrics:
                values = tuple(float(getattr(row, metric)) for row in selected)
                boot = sorted(
                    sum(rng.choice(values) for _ in values) / len(values)
                    for _ in range(samples)
                )
                result["by_condition"][condition_key][system][metric] = {
                    "mean": sum(values) / len(values),
                    "ci95_low": _percentile(boot, 0.025),
                    "ci95_high": _percentile(boot, 0.975),
                    "n_seeds": len(values),
                }
    return result


def _percentile(sorted_values: list[float], quantile: float) -> float:
    index = quantile * (len(sorted_values) - 1)
    lower = int(index)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = index - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction
