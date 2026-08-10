"""Sealed deterministic provenance-security experiment."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .bypass import run_bypass_probes
from .experiment import seal_run
from .threats import (
    evaluate_governed_threats,
    evaluate_threats,
    generate_threat_scenarios,
)


def run_security_experiment(config: dict[str, Any], output: Path) -> Path:
    if output.exists():
        raise FileExistsError(f"immutable run already exists: {output}")
    seed = int(config["seed"])
    scenarios = generate_threat_scenarios(seed)
    output.mkdir(parents=True)
    _write_json(
        output / "scenarios.json",
        [
            {
                "scenario_id": scenario.scenario_id,
                "attack_type": scenario.attack_type,
                "malicious": scenario.malicious,
                "evidence_ids": [item.belief_id for item in scenario.evidence],
                "ancestor_ids": [item.belief_id for item in scenario.ancestors],
            }
            for scenario in scenarios
        ],
    )
    _write_json(
        output / "results.json",
        {
            "undefended": asdict(evaluate_threats(scenarios, defended=False)),
            "provenance_gate": asdict(evaluate_threats(scenarios, defended=True)),
            "governed": asdict(evaluate_governed_threats(seed)),
            "adaptive_bypass": [asdict(item) for item in run_bypass_probes()],
        },
    )
    seal_run(
        output,
        config=config,
        command=f"temvera security-experiment <config> {output}",
    )
    return output


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
