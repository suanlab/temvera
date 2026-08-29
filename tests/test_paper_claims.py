"""The paper's numbers are part of the test suite, not a manual review step.

An audit found seven figures in one subsection had drifted onto runs the paper
does not use, including one it explicitly disowns. Nothing failed, because
nothing checked. This runs the claim verifier as a test so that editing a number
by hand, or re-sealing a run without updating the prose, breaks the build.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_every_paper_claim_matches_its_sealed_run() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_paper_claims.py")],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "every claim matches" in result.stdout
