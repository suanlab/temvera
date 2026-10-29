"""H19: the temporal positive control.

    python scripts/analyze_h19.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_corrections  # noqa: E402
import analyze_purge_scope  # noqa: E402

from temvera.reanalysis import load_run, matched_cells  # noqa: E402

RUNS = ROOT / "experiments" / "runs"
GRID, FINAL = "positive-control-grid-v1", "positive-control-final-store-v1"
GRID_SYSTEMS = ("external-mem0-grid-v2", "external-langmem-v1", "external-graphiti-hybrid-v1",
                "external-cognee-chunks-grid-v3", "external-cognee-grid-v1",
                "external-hindsight-recall-v1", "external-hindsight-reflect-v1")


def cells() -> set:
    return matched_cells(*(load_run(RUNS / r) for r in GRID_SYSTEMS))


def grid() -> dict:
    return analyze_purge_scope.overall(GRID, cells())


def final_store() -> dict:
    return analyze_corrections.pre_correction(FINAL)


def unparsed() -> int:
    total = 0
    for run in (GRID, FINAL):
        total += json.loads((RUNS / run / "results.json").read_text())["backbone"]["unparsed_turns"]
    return total


def checks() -> dict[str, bool]:
    g, f = grid(), final_store()
    rows = [json.loads(line) for line in (RUNS / FINAL / "transcript.jsonl").read_text().splitlines()]
    return {"H19a": g["request_scope"] == g["questions"],
            "H19b": g["as_specified"] == g["questions"] - 29,
            "H19c": f["strict"] == f["questions"] == 45 and all(r["exact"] for r in rows),
            "H19d": unparsed() == 0}


def main() -> int:
    print("grid", grid(), "final store", final_store(), "unparsed", unparsed())
    print(checks())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
