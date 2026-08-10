"""Freeze small deterministic lifecycle splits with provenance manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .generator import generate_histories


SPLITS = {"train": 101, "development": 202, "test": 303}


def freeze_dataset(
    output: Path, *, entities: int = 8, revisions: int = 4
) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"frozen dataset path already exists: {output}")
    output.mkdir(parents=True)
    split_manifest: dict[str, dict[str, object]] = {}
    for split, seed in SPLITS.items():
        events = generate_histories(
            seed=seed,
            entities=entities,
            revisions=revisions,
            namespace=split,
        )
        path = output / f"{split}.jsonl"
        with path.open("w", encoding="utf-8") as stream:
            for event in events:
                stream.write(
                    json.dumps(event.to_dict(), sort_keys=True, ensure_ascii=False)
                    + "\n"
                )
        split_manifest[split] = {
            "events": len(events),
            "seed": seed,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    manifest: dict[str, object] = {
        "entities_per_split": entities,
        "generator": "temvera.generator.generate_histories",
        "license": "Apache-2.0",
        "name": "temvera-lifecycle-v0",
        "personal_or_sensitive_data": "none; fully synthetic labels",
        "redistribution": "permitted under the repository Apache-2.0 license",
        "revisions_per_entity": revisions,
        "splits": split_manifest,
        "test_tuning": "prohibited; tune only on train/development",
        "timestamp_policy": "wall-clock time omitted for byte reproducibility",
        "version": "0.1.0",
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(dataset_card(manifest), encoding="utf-8")
    return manifest


def verify_dataset(path: Path) -> bool:
    manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
    identifiers: dict[str, set[str]] = {}
    for split, metadata in manifest["splits"].items():
        split_path = path / f"{split}.jsonl"
        actual = hashlib.sha256(split_path.read_bytes()).hexdigest()
        if actual != metadata["sha256"]:
            return False
        rows = [json.loads(line) for line in split_path.read_text(encoding="utf-8").splitlines()]
        if len(rows) != metadata["events"]:
            return False
        identifiers[split] = (
            {row["belief_id"] for row in rows}
            | {row["event_id"] for row in rows}
            | {row["subject"] for row in rows if row.get("subject")}
        )
    for left, left_ids in identifiers.items():
        for right, right_ids in identifiers.items():
            if left < right and left_ids & right_ids:
                return False
    return True


def dataset_card(manifest: dict[str, object]) -> str:
    return f"""# Temvera lifecycle v0 dataset card

## Summary

This is a fully synthetic, seed-frozen event stream for testing bitemporal
ingest and supersession semantics. It contains no conversations, model output,
or personal data. Version: `{manifest['version']}`.

## Splits and intended use

Train and development may be used for implementation and threshold selection.
The test split is evaluation-only. Each split uses disjoint generated entity
labels and a fixed seed recorded in `manifest.json`.

## Limitations

Template labels do not model natural-language ambiguity, entity resolution,
realistic update rates, or social context. Scores measure mechanism correctness,
not real-world agent quality. Reconfirmation, expiry, purge, and attacks are
covered by deterministic test fixtures but are not yet included in this v0
bulk split.

## License and redistribution

{manifest['redistribution']}. Third-party datasets are not included or covered.
"""
