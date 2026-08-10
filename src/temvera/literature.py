"""Validation and deterministic freeze tooling for the prior-art review."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


LEDGER_ID = re.compile(r"E-\d{3}")


def freeze_review(review_dir: Path, ledger_path: Path, output: Path) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    studies_path = review_dir / "studies.csv"
    search_path = review_dir / "search-log.csv"
    exclusions_path = review_dir / "exclusions.csv"
    rescreen_path = review_dir / "rescreen-log.csv"
    studies = _read_unique_rows(studies_path, "study_id")
    searches = _read_unique_rows(search_path, "search_id")
    exclusions = _read_unique_rows(exclusions_path, "exclusion_id")
    rescreens = _read_unique_rows(rescreen_path, "study_id")
    ledger_text = ledger_path.read_text(encoding="utf-8")
    known_ledger_ids = set(LEDGER_ID.findall(ledger_text))
    missing = sorted(
        {
            evidence_id
            for row in studies
            for evidence_id in LEDGER_ID.findall(row.get("evidence_ids", ""))
            if evidence_id not in known_ledger_ids
        }
    )
    if missing:
        raise ValueError(f"unknown evidence ledger IDs: {missing}")
    sample_size = max(1, (len(studies) + 9) // 10)
    rescreen_ids = sorted(
        (row["study_id"] for row in studies),
        key=lambda value: hashlib.sha256(value.encode()).hexdigest(),
    )[:sample_size]
    completed_rescreens = {row["study_id"] for row in rescreens}
    if completed_rescreens != set(rescreen_ids):
        raise ValueError(
            "rescreen log must exactly cover deterministic sample: "
            f"expected {rescreen_ids}, got {sorted(completed_rescreens)}"
        )
    files = (studies_path, search_path, exclusions_path, ledger_path)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "counts": {
            "studies": len(studies),
            "searches": len(searches),
            "exclusions": len(exclusions),
            "rescreens": len(rescreens),
        },
        "single_screened": sum(
            row.get("review_state") == "single_screened" for row in studies
        ),
        "rescreen_sample_ids": rescreen_ids,
        "rescreened_ids": sorted(row["study_id"] for row in rescreens),
        "sha256": {
            str(path.relative_to(review_dir.parent.parent))
            if path.is_relative_to(review_dir.parent.parent)
            else path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (*files, rescreen_path)
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_review_freeze(review_dir: Path, ledger_path: Path, manifest_path: Path) -> bool:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    root = review_dir.parent.parent
    return all(
        (root / relative).is_file()
        and hashlib.sha256((root / relative).read_bytes()).hexdigest() == digest
        for relative, digest in manifest["sha256"].items()
    )


def _read_unique_rows(path: Path, key: str) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or key not in reader.fieldnames:
            raise ValueError(f"{path} is missing required column {key}")
        rows = list(reader)
    values = [row[key].strip() for row in rows]
    if any(not value for value in values):
        raise ValueError(f"{path} contains an empty {key}")
    if len(values) != len(set(values)):
        raise ValueError(f"{path} contains duplicate {key}")
    return rows
