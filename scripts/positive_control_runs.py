"""H19: the temporal positive control on the paper's two workloads.

Runs :class:`temvera.positive_control.PositiveControl` -- bitemporal predicates
over the rendered text, no LLM -- through the same harness, histories and
scorer as the five systems:

* the main grid (the cells of ``external-mem0-grid-v2``), forward-checkpoint
  replay, into ``positive-control-grid-v1``;
* the H11 final-store correction histories (the cells of
  ``final-store-corrections-hindsight-reflect-v1``), one pass, into
  ``positive-control-final-store-v1``.

    python scripts/positive_control_runs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from temvera.experiment import seal_run
from temvera.external_experiment import run_external_comparison
from temvera.positive_control import PositiveControl

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments" / "runs"
SOURCES = {"positive-control-grid-v1": "external-mem0-grid-v2",
           "positive-control-final-store-v1": "final-store-corrections-hindsight-reflect-v1"}
DROP = ("backbone", "benchmark", "model", "embed_model", "user_id", "bank_prefix", "read_mode",
        "search_limit")


def main() -> int:
    for output in SOURCES:
        if (RUNS / output).exists():
            raise SystemExit(f"refusing to overwrite: {RUNS / output}")
    for output, source in SOURCES.items():
        source_config = json.loads((RUNS / source / "config.json").read_text(encoding="utf-8"))
        config = {k: v for k, v in source_config.items() if k not in DROP}
        made: list[PositiveControl] = []

        def factory(label: str) -> PositiveControl:
            made.append(PositiveControl())
            return made[-1]

        result = run_external_comparison(config, factory, system_name="positive-control")
        unparsed = [t for system in made for t in system.unparsed]
        result["backbone"] = {"system": "positive-control", "llm": None, "replay": result["replay"],
                              "unparsed_turns": len(unparsed), "worker_errors": 0}
        transcript = result.pop("transcript")
        out = RUNS / output
        out.mkdir(parents=True)
        (out / "results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with (out / "transcript.jsonl").open("w", encoding="utf-8") as handle:
            for row in transcript:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        seal_run(out, config={**config, "benchmark": f"temvera-{output}", "source_config_of": source,
                              "system": "positive-control", "backbone": result["backbone"]},
                 command="python scripts/positive_control_runs.py")
        print(output, {"cases": len(transcript), "exact": sum(r["exact"] for r in transcript),
                       "unparsed": len(unparsed)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main(*sys.argv[1:]))
