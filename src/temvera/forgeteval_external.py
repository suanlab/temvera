"""Pinned, immutable execution wrapper for the external ForgetEval generator."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

from .forgeteval import ForgetEvalAdapter


def run_forgeteval(
    source_root: Path,
    output: Path,
    *,
    expected_commit: str,
    scale: int,
    seed: int,
    distractors: int,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    if scale <= 0 or distractors < 0:
        raise ValueError("scale must be positive and distractors non-negative")
    actual_commit = subprocess.run(
        ["git", "-C", str(source_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if actual_commit != expected_commit:
        raise ValueError(f"source commit mismatch: {actual_commit}")

    generator_path = source_root / "bench" / "forgeteval" / "generate.py"
    module = _load_module(generator_path)
    cases = module.generate(scale, seed=seed, distractors=distractors)
    adapter = ForgetEvalAdapter()
    predictions = [
        {"case_id": case.id, "family": case.family, "passed": case.run(adapter)}
        for case in cases
    ]
    family_counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for row in predictions:
        family_counts[row["family"]][1] += 1
        family_counts[row["family"]][0] += int(row["passed"])
    metrics = {
        "cases": len(predictions),
        "passed": sum(int(row["passed"]) for row in predictions),
        "pass_rate": sum(int(row["passed"]) for row in predictions) / len(predictions),
        "by_family": dict(sorted(family_counts.items())),
    }
    config = {
        "adapter": adapter.name,
        "source_commit": actual_commit,
        "scale": scale,
        "seed": seed,
        "distractors": distractors,
    }
    output.mkdir(parents=True)
    _write_json(output / "config.json", config)
    _write_json(output / "metrics.json", metrics)
    _write_json(output / "predictions.json", predictions)
    checksums = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.iterdir())
    }
    _write_json(output / "checksums.json", checksums)
    return metrics


def _load_module(path: Path) -> ModuleType:
    if not path.is_file():
        raise FileNotFoundError(path)
    spec = importlib.util.spec_from_file_location("temvera_pinned_forgeteval", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    return module


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
