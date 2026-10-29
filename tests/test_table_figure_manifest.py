"""Every table and figure is mapped to its runs and code, and the shipped map is
current (CHECK.md F11)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import table_figure_manifest  # noqa: E402


def test_shipped_manifest_is_current() -> None:
    shipped = json.loads((ROOT / "docs" / "table-figure-manifest.json").read_text(encoding="utf-8"))
    assert shipped == table_figure_manifest.manifest()
