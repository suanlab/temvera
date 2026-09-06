"""The artifact's byte-reproducibility is a claim, so it is tested.

A pinned checksum in a tracked file cannot guard this: it goes stale on the next
commit that touches packaged content, and a stale pin is worse than none. What
is stable, and what the reproducibility claim actually rests on, is that two
builds of the same tree agree byte for byte.
"""

from __future__ import annotations

from pathlib import Path
import hashlib

from temvera.artifact import create_artifact_archive, verify_artifact_archive

ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_artifact_package_is_byte_reproducible(tmp_path) -> None:
    first, second = tmp_path / "a.tar.gz", tmp_path / "b.tar.gz"
    create_artifact_archive(ROOT, first)
    create_artifact_archive(ROOT, second)
    assert _sha256(first) == _sha256(second)
    assert verify_artifact_archive(first)


def test_checksum_file_pins_nothing_that_can_go_stale() -> None:
    text = (ROOT / "ARTIFACT-CHECKSUMS.txt").read_text(encoding="utf-8")
    import re

    assert not re.search(r"\b[a-f0-9]{64}\b", text), (
        "a pinned hash here invalidates itself on the next commit; "
        "pin it in the release notes instead"
    )
