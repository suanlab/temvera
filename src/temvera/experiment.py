"""Immutable, self-describing deterministic experiment runs."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .evaluation import (
    AppendOnlyBaseline,
    BM25Baseline,
    FullContextBaseline,
    LastWriteWinsBaseline,
    RecentContextBaseline,
    cases_from_oracle,
    error_analysis,
    evaluate,
)
from .generator import generate_histories
from .oracle import LifecycleOracle


def run_lifecycle_experiment(config: dict[str, Any], output_root: Path) -> Path:
    dataset = config["dataset"]
    events = generate_histories(
        seed=int(dataset["seed"]),
        entities=int(dataset["entities"]),
        revisions=int(dataset["revisions"]),
    )
    cases = cases_from_oracle(events)
    systems = {
        "oracle": LifecycleOracle(events),
        "append_only": AppendOnlyBaseline(events),
        "full_context": FullContextBaseline(events),
        "recent_context": RecentContextBaseline(events),
        "bm25_at_1": BM25Baseline(events, limit=1),
        "last_write_wins": LastWriteWinsBaseline(events),
    }
    metrics = {name: asdict(evaluate(system, cases)) for name, system in systems.items()}
    errors = {
        name: [asdict(error) for error in error_analysis(system, cases)]
        for name, system in systems.items()
    }
    canonical_config = _canonical(config)
    source_hash = hash_source_tree(Path(__file__).resolve().parents[2] / "src")
    run_hash = hashlib.sha256(canonical_config + source_hash.encode()).hexdigest()[:12]
    run_id = f"lifecycle-{run_hash}"
    run_dir = output_root / run_id
    if run_dir.exists():
        raise FileExistsError(f"immutable run already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    (run_dir / "config.json").write_bytes(canonical_config + b"\n")
    environment = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": git_revision(Path.cwd()),
        "platform": platform.platform(),
        "python": sys.version,
        "source_sha256": source_hash,
    }
    _write_json(run_dir / "environment.json", environment)
    _write_json(run_dir / "metrics.json", metrics)
    _write_json(run_dir / "error-analysis.json", errors)
    with (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as stream:
        for case in cases:
            for name, system in systems.items():
                returned = system.query(
                    case.subject,
                    case.attribute,
                    valid_at=case.valid_at,
                    transaction_at=case.transaction_at,
                )
                row = {
                    "case_id": case.case_id,
                    "expected_ids": sorted(case.expected_ids),
                    "returned_ids": sorted(item.belief_id for item in returned),
                    "system": name,
                }
                stream.write(json.dumps(row, sort_keys=True) + "\n")
    stdout = json.dumps(metrics, sort_keys=True) + "\n"
    (run_dir / "stdout.log").write_text(stdout, encoding="utf-8")
    readme = (
        "# Lifecycle experiment run\n\n"
        f"- Run ID: `{run_id}`\n"
        "- Hypothesis: lifecycle-aware state matches the bitemporal oracle and "
        "exposes stale baseline results.\n"
        f"- Cases: {len(cases)}\n"
        "- Interpretation: mechanism-isolation result; no external validity or "
        "novelty claim.\n"
    )
    (run_dir / "README.md").write_text(readme, encoding="utf-8")
    _write_json(run_dir / "checksums.json", checksums(run_dir))
    return run_dir


def hash_source_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def checksums(run_dir: Path) -> dict[str, str]:
    return {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(run_dir.iterdir())
        if path.is_file() and path.name != "checksums.json"
    }


def seal_run(
    run_dir: Path,
    *,
    config: dict[str, Any],
    command: str,
    source_root: Path | None = None,
) -> None:
    """Seal an existing immutable run without rewriting its raw result files."""
    if not run_dir.is_dir():
        raise FileNotFoundError(f"run directory does not exist: {run_dir}")
    reserved = ("config.json", "environment.json", "checksums.json")
    present = [name for name in reserved if (run_dir / name).exists()]
    if present:
        raise FileExistsError(f"run is already sealed or ambiguous: {present}")
    raw_files = tuple(path for path in run_dir.iterdir() if path.is_file())
    if not raw_files:
        raise ValueError("cannot seal a run without raw result files")
    root = source_root or Path(__file__).resolve().parents[2] / "src"
    (run_dir / "config.json").write_bytes(_canonical(config) + b"\n")
    _write_json(
        run_dir / "environment.json",
        {
            "command": command,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "git_revision": git_revision(Path.cwd()),
            "platform": platform.platform(),
            "python": sys.version,
            "source_sha256": hash_source_tree(root),
        },
    )
    _write_json(run_dir / "checksums.json", checksums(run_dir))


def verify_run(run_dir: Path) -> bool:
    """Verify that every sealed file is present and byte-identical."""
    checksum_path = run_dir / "checksums.json"
    if not checksum_path.is_file():
        return False
    try:
        recorded = json.loads(checksum_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if not isinstance(recorded, dict) or not all(
        isinstance(name, str) and isinstance(digest, str)
        for name, digest in recorded.items()
    ):
        return False
    return recorded == checksums(run_dir)


def verify_run_set(output_root: Path, manifest_path: Path) -> bool:
    """Verify an allowlisted set of sealed experiment directories."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_ids = manifest["accepted_runs"]
    except (KeyError, json.JSONDecodeError, OSError, TypeError):
        return False
    if not isinstance(run_ids, list) or not all(
        isinstance(run_id, str)
        and run_id
        and Path(run_id).name == run_id
        and run_id not in {".", ".."}
        for run_id in run_ids
    ):
        return False
    if len(run_ids) != len(set(run_ids)):
        return False
    return bool(run_ids) and all(verify_run(output_root / run_id) for run_id in run_ids)


def git_revision(directory: Path) -> str | None:
    result = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=directory,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
