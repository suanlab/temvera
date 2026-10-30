"""Where each table and figure of the paper comes from.

The tables are hand-written TeX; their numbers are checked by
``verify_paper_claims.py``. This writes, for every table and figure label in
``paper/main.tex``, its caption's opening, the sealed runs it rests on, the code
that computes it, how it aggregates, and how many checked claims sit inside it
(counted from the claims' anchors, not declared). A label missing from the map
below is an error, so a new table cannot go unmapped.

    python scripts/table_figure_manifest.py [--write docs/table-figure-manifest.json]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

GRID = ["external-mem0-grid-v2", "external-langmem-v1", "external-graphiti-hybrid-v1",
        "external-cognee-chunks-grid-v3", "external-cognee-grid-v1", "external-hindsight-recall-v1",
        "external-hindsight-reflect-v1"]
LME = [f"lme-bitemporal-{s}-{part}" for s, part in (
    ("mem0", "agreement-v1"), ("mem0", "adjudicated-v1"), ("langmem", "agreement-v1"),
    ("langmem", "adjudicated-v1"), ("graphiti", "agreement-v1"), ("graphiti", "adjudicated-v1"),
    ("cognee-chunks", "agreement-v3"), ("cognee-chunks", "adjudicated-v1"),
    ("hindsight-recall", "agreement-v2"), ("hindsight-recall", "adjudicated-v1"),
    ("cognee-graph", "agreement-v3"), ("cognee-graph", "adjudicated-v1"),
    ("hindsight-reflect", "agreement-v2"), ("hindsight-reflect", "adjudicated-v1"))]
SYSTEMS = ("mem0", "langmem", "graphiti", "cognee", "hindsight")

MAP = {
    "tab:related": {"runs": [], "code": "none: read from each work's full text and released code",
                    "aggregation": "qualitative", "sources": ["data/literature/"]},
    "tab:fragment": {"runs": ["store-census-v1"],
                     "code": "scripts/store_census.py; capability audit of the installed distributions",
                     "aggregation": "qualitative levels; counts are case counts"},
    "tab:claims": {"runs": ["external-graphiti-hybrid-v1", "external-hindsight-recall-v1",
                            "external-cognee-chunks-grid-v3", "external-mem0-grid-v2", "external-langmem-v1",
                            "h9-reader-graphiti-v1", "h9-reader-hindsight-recall-v1",
                            "h9-reader-cognee-chunks-v1", "h9-reader-mem0-v1", "h9-reader-langmem-v1"],
                   "code": "temvera.reanalysis.category_counts; scripts/llm_rescore.py (reader)",
                   "aggregation": "case-weighted", "sources": ["data/literature/system-claims-2026-08-20.json"]},
    "tab:settings": {"runs": GRID, "code": "configs under experiments/configs/; run config.json",
                     "aggregation": "settings, no numbers computed"},
    "tab:external": {"runs": GRID[:3],
                     "code": "temvera.reanalysis.category_counts; scripts/analyze_purge_scope.py (purge, overall)",
                     "aggregation": "case-weighted rates; recall and stale-use cell-averaged as sealed"},
    "fig:categories": {"runs": GRID, "code": "scripts/make_figures.py:figure_categories",
                       "aggregation": "case-weighted with Wilson 95% intervals"},
    "fig:budget": {"runs": GRID[:3], "code": "scripts/make_figures.py:figure_budget "
                                             "(analyze_purge_scope.overall per k)",
                   "aggregation": "case-weighted"},
    "tab:deletion": {"runs": [f"deletion-study-{s}-v1" for s in SYSTEMS]
                     + [f"deletion-verified-{s}-v1" for s in SYSTEMS] + ["deletion-langmem-deletes-v1"],
                     "code": "temvera.deletion_study.summarize",
                     "aggregation": "counts of people (of 24 purged, 36 never purged) and histories (of 9)"},
    "tab:reader": {"runs": GRID + ["h9-reader-mem0-v1", "h9-reader-langmem-v1", "h9-reader-graphiti-v1",
                                   "h9-reader-cognee-chunks-v1", "h9-reader-hindsight-recall-v1",
                                   "h9-judge-gpt4o-cognee-graph-v1", "h9-judge-gpt4o-hindsight-reflect-v1"],
                   "code": "temvera.reanalysis; scripts/analyze_purge_scope.py; scripts/llm_rescore.py",
                   "aggregation": "case-weighted"},
    "tab:growth": {"runs": ["scale-growth-mem0-v1", "scale-growth-graphiti-v1", "scale-growth-hindsight-v1"],
                   "code": "scripts/analyze_scale_cost.py", "aggregation": "per checkpoint; p95 over 40-80 questions"},
    "tab:scale": {"runs": ["scale-sweep-mem0-e8-v2", "scale-sweep-mem0-e32-v2"]
                  + [f"scale-sweep-mem0-e128-s{s}-v3" for s in (7, 17, 42)]
                  + [f"scale-sweep-graphiti-e{e}-v2" for e in (8, 32, 128)],
                  "code": "scripts/verify_paper_claims.py:scale_rate", "aggregation": "case-weighted, Wilson 95%"},
    "tab:realdata": {"runs": LME, "code": "temvera.lme_bitemporal; run summaries summed over the two label sets",
                     "aggregation": "counts of 62 pairs (60 for valid time)"},
    "tab:releases": {"runs": ["external-mem0-grid-latest-v1", "external-graphiti-hybrid-latest-v1",
                              "external-cognee-chunks-grid-latest-v1", "external-cognee-grid-latest-v1",
                              "external-hindsight-recall-latest-v1", "external-hindsight-reflect-latest-v1"]
                     + GRID,
                     "code": "temvera.reanalysis.category_counts; scripts/analyze_purge_scope.py",
                     "aggregation": "case-weighted"},
}


def floats(tex: str) -> list[tuple[str, int, int, str]]:
    """(label, start, end, caption opening) for every table and figure."""
    out = []
    for m in re.finditer(r"\\begin\{(table|figure)\*?\}.*?\\end\{\1\*?\}", tex, re.S):
        label = re.search(r"\\label\{((?:tab|fig):[^}]+)\}", m.group(0))
        caption = re.search(r"\\caption\{(.{0,140})", m.group(0), re.S)
        if label:
            text = re.sub(r"\s+", " ", caption.group(1)).strip() if caption else ""
            out.append((label.group(1), m.start(), m.end(), text))
    return out


def claims_inside(tex: str) -> dict[str, int]:
    import verify_paper_claims as v

    spans = floats(tex)
    counts = {label: 0 for label, *_ in spans}
    for claim in v.CLAIMS:
        if claim.near is None:
            continue
        start = tex.find(claim.after) if claim.after is not None else 0
        spot = tex.find(claim.near, max(start, 0)) if start >= 0 else -1
        for label, a, b, _ in spans:
            if a <= spot < b:
                counts[label] += 1
    return counts


def manifest() -> dict:
    tex = (ROOT / "paper" / "main.tex").read_text(encoding="utf-8")
    spans = floats(tex)
    missing = [label for label, *_ in spans if label not in MAP]
    if missing:
        raise SystemExit(f"unmapped tables or figures: {missing}")
    counts = claims_inside(tex)
    accepted = set(json.loads((ROOT / "experiments" / "accepted-runs.json").read_text())["accepted_runs"])
    entries = []
    for label, _, _, caption in spans:
        entry = MAP[label]
        unknown = [r for r in entry["runs"] if r not in accepted]
        if unknown:
            raise SystemExit(f"{label}: runs not accepted: {unknown}")
        entries.append({"label": label, "caption_opening": caption, **entry,
                        "checked_claims_inside": counts[label]})
    return {"note": "Tables are hand-written TeX; every number in them is checked by "
                    "scripts/verify_paper_claims.py. Claims anchored in prose about a table "
                    "are not counted here.", "floats": entries}


def main(argv: list[str]) -> int:
    data = manifest()
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    if "--write" in argv:
        Path(argv[argv.index("--write") + 1]).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
