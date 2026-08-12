import gzip
import hashlib
import io
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


def test_artifact_verification_detects_content_tampering(tmp_path) -> None:
    """Rewriting a member's bytes must fail the manifest comparison."""
    root = tmp_path / "root"
    root.mkdir()
    _fixture(root)
    archive = tmp_path / "a.tar.gz"
    create_artifact_archive(root, archive)
    assert verify_artifact_archive(archive)

    with tarfile.open(archive, "r:gz") as source:
        members = [(m, source.extractfile(m.name).read()) for m in source.getmembers()]
    tampered = tmp_path / "tampered.tar.gz"
    with gzip.GzipFile(filename="", mode="wb", fileobj=tampered.open("wb"), mtime=0) as gz:
        with tarfile.open(fileobj=gz, mode="w", format=tarfile.PAX_FORMAT) as out:
            for member, payload in members:
                if member.name == "README.md":
                    payload = payload + b"tampered"
                    member.size = len(payload)
                out.addfile(member, io.BytesIO(payload))
    assert not verify_artifact_archive(tampered)


def test_artifact_verification_detects_envelope_corruption(tmp_path) -> None:
    """Any single-byte flip must fail, including gzip framing or tar padding.

    Member checksums alone can miss this, so verification also decodes the gzip
    stream to force its CRC check.
    """
    root = tmp_path / "root"
    root.mkdir()
    _fixture(root)
    archive = tmp_path / "b.tar.gz"
    create_artifact_archive(root, archive)
    original = archive.read_bytes()
    # Sweep several offsets rather than one: the previous single-offset test was
    # flaky because a flip can land where it does not alter member content.
    for fraction in (0.25, 0.5, 0.75, 0.9):
        offset = int(len(original) * fraction)
        payload = bytearray(original)
        payload[offset] ^= 1
        archive.write_bytes(payload)
        assert not verify_artifact_archive(archive), f"missed corruption at {offset}"
