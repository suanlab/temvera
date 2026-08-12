"""Regenerate paper figures from sealed run artifacts.

Every figure is derived from `experiments/runs/*/results.json` or
`transcript.jsonl` via `temvera.reanalysis`, so figures cannot drift from the
numbers in the evidence ledger. Run:

    python scripts/make_figures.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from temvera.reanalysis import (  # noqa: E402
    category_counts,
    k_sweep,
    load_run,
    load_transcript,
    matched_cells,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "experiments" / "runs"
OUT = ROOT / "paper" / "figures"
MEM0 = RUNS / "external-mem0-grid-v1"
GRAPHITI = RUNS / "external-graphiti-scale-v1"
CATEGORIES = ("transaction_as_of", "valid_time", "expiry_boundary", "purge")
LABELS = {
    "transaction_as_of": "transaction\nas-of",
    "valid_time": "valid time\n(historical)",
    "expiry_boundary": "expiry\nboundary",
    "purge": "purge\n(deletion)",
}


def _cells():
    return matched_cells(load_run(MEM0), load_run(GRAPHITI))


def figure_categories(cells) -> None:
    """Per-category exact accuracy with Wilson intervals, matched cells."""
    mem0 = category_counts(load_transcript(MEM0), cells=cells)
    graphiti = category_counts(load_transcript(GRAPHITI), cells=cells)
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    width = 0.38
    for offset, (name, data, colour) in enumerate(
        (("Mem0", mem0, "#3b6ea5"), ("Graphiti", graphiti, "#c2703d"))
    ):
        xs, ys, lo, hi = [], [], [], []
        for index, category in enumerate(CATEGORIES):
            p = data.get(category)
            if p is None:
                continue
            low, high = p.wilson()
            xs.append(index + (offset - 0.5) * width)
            ys.append(p.rate)
            lo.append(p.rate - low)
            hi.append(high - p.rate)
        ax.bar(xs, ys, width, label=name, color=colour)
        ax.errorbar(xs, ys, yerr=[lo, hi], fmt="none", ecolor="black", capsize=3, lw=1)
    ax.axhline(1.0, ls="--", lw=1, color="grey")
    ax.text(3.45, 1.02, "oracle = 1.0 (by construction)", ha="right", fontsize=8, color="grey")
    ax.set_xticks(range(len(CATEGORIES)))
    ax.set_xticklabels([LABELS[c] for c in CATEGORIES], fontsize=9)
    ax.set_ylabel("exact accuracy")
    ax.set_ylim(0, 1.12)
    ax.legend(frameon=False, loc="upper right")
    ax.set_title(
        "Per-category exact accuracy, 20 matched cells (Wilson 95% intervals)",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(OUT / "categories.pdf")
    plt.close(fig)


def figure_budget(cells) -> None:
    """Exact accuracy versus retrieval budget k — the confound reviewers found."""
    budgets = (1, 2, 3, 5)
    mem0 = k_sweep(load_transcript(MEM0), budgets=budgets, cells=cells)
    graphiti = k_sweep(load_transcript(GRAPHITI), budgets=budgets, cells=cells)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, metric, title in (
        (axes[0], "overall", "overall exact"),
        (axes[1], "valid_time", "valid-time exact"),
    ):
        for name, data, colour, marker in (
            ("Mem0", mem0, "#3b6ea5", "o"),
            ("Graphiti", graphiti, "#c2703d", "s"),
        ):
            ys = []
            for k in budgets:
                entry = data[k]
                ys.append(
                    entry["overall"]["rate"]
                    if metric == "overall"
                    else entry["by_category"].get(metric, {}).get("rate", float("nan"))
                )
            ax.plot(budgets, ys, marker=marker, color=colour, label=name)
        ax.set_xlabel("retrieval budget $k$")
        ax.set_title(title, fontsize=10)
        ax.set_xticks(budgets)
        ax.set_ylim(0, 1.0)
    axes[0].set_ylabel("exact accuracy")
    axes[0].legend(frameon=False)
    fig.suptitle(
        "Scoring is budget-dependent: Graphiti's deficit appears only as $k$ grows",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(OUT / "budget.pdf")
    plt.close(fig)


def figure_residual() -> None:
    """Where purged payloads survive, split by reachability class."""
    import json

    label = {"temvera": "Temvera", "mem0": "Mem0", "graphiti": "Graphiti"}
    # Append-only audit logs are not read by any query path; everything else is
    # reachable from retrieval.
    audit_stores = {"raw_ledger_jsonl", "mem0_history_sqlite"}
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0), sharey=True)
    for ax, tag, title in (
        (axes[0], "nl", "natural-language instruction"),
        (axes[1], "api", "native deletion API"),
    ):
        data = json.loads(
            (RUNS / f"purge-residual-v3-{tag}" / "results.json").read_text("utf-8")
        )
        reach = {"Temvera": 0, "Mem0": 0, "Graphiti": 0}
        audit = {"Temvera": 0, "Mem0": 0, "Graphiti": 0}
        for report in data["reports"]:
            name = label[report["system"]]
            for store in report["stores"]:
                bucket = audit if store["store"] in audit_stores else reach
                bucket[name] += max(0, store["occurrences"])
        names = list(reach)
        ax.bar(names, [reach[n] for n in names], label="retrieval-reachable", color="#b3462f")
        ax.bar(
            names,
            [audit[n] for n in names],
            bottom=[reach[n] for n in names],
            label="append-only log (not queried)",
            color="#c9c9c9",
        )
        ax.set_title(title, fontsize=10)
    axes[0].set_ylabel("residual occurrences")
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Deletion works through the API; prose deletion intent does not survive extraction",
        fontsize=10,
    )
    fig.tight_layout()
    fig.savefig(OUT / "residual.pdf")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cells = _cells()
    figure_categories(cells)
    figure_budget(cells)
    figure_residual()
    print(f"wrote figures to {OUT} over {len(cells)} matched cells")


if __name__ == "__main__":
    main()
