import hashlib
import json
from pathlib import Path
import tarfile

from temvera.artifact import create_artifact_archive, verify_artifact_archive
from temvera.experiment import seal_run


def _fixture(root: Path) -> None:
    for name in (
        "AGENTS.md",
        "CITATION.cff",
        "CONTRIBUTING.md",
        "LICENSE",
        "README.md",
        "REPRODUCING.md",
        "pyproject.toml",
    ):
        (root / name).write_text(name, encoding="utf-8")
    for directory in ("src", "tests", "docs", "data", "experiments/configs"):
        path = root / directory
        path.mkdir(parents=True)
        (path / "fixture.txt").write_text(directory, encoding="utf-8")
    run = root / "experiments" / "runs" / "run-1"
    run.mkdir(parents=True)
    (run / "results.json").write_text("{}\n", encoding="utf-8")
    seal_run(run, config={}, command="fixture", source_root=root / "src")
    (root / "experiments" / "accepted-runs.json").write_text(
        json.dumps({"accepted_runs": ["run-1"]}), encoding="utf-8"
    )


def test_artifact_archive_is_deterministic_and_detects_tamper(tmp_path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _fixture(root)
    first = tmp_path / "first.tar.gz"
    second = tmp_path / "second.tar.gz"
    create_artifact_archive(root, first)
    create_artifact_archive(root, second)
    assert hashlib.sha256(first.read_bytes()).digest() == hashlib.sha256(
        second.read_bytes()
    ).digest()
    assert verify_artifact_archive(first)
    with tarfile.open(first, "r:gz") as archive:
        manifest = json.load(archive.extractfile("ARTIFACT-MANIFEST.json"))
    assert manifest["redistribution_status"] == "permitted_under_apache_2_0"
    payload = bytearray(first.read_bytes())
    payload[len(payload) // 2] ^= 1
    first.write_bytes(payload)
    assert not verify_artifact_archive(first)
