"""Historical runs stay out of the main tables, figures and recompute command.

They stay accepted, because they are evidence of what happened, but the paper's
current results must not be computed from them (CHECK.md F03)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "experiments" / "run-status.json").read_text(encoding="utf-8"))


def test_historical_runs_are_accepted_runs() -> None:
    accepted = set(json.loads((ROOT / "experiments" / "accepted-runs.json").read_text())["accepted_runs"])
    assert set(STATUS["historical"]) <= accepted


def test_main_results_do_not_read_historical_runs() -> None:
    for script in ("make_figures.py", "recompute_paper_numbers.py", "analyze_purge_scope.py"):
        text = (ROOT / "scripts" / script).read_text(encoding="utf-8")
        used = [run for run in STATUS["historical"] if f'"{run}"' in text or f"/ \"{run}\"" in text]
        assert not used, f"{script} reads historical runs {used}"
