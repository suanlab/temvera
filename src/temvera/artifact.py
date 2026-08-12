"""Deterministic local artifact packaging with an internal checksum manifest."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zlib
from typing import Any

from .experiment import verify_run_set


ROOT_FILES = (
    "AGENTS.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.md",
    "REPRODUCING.md",
    "pyproject.toml",
)
ROOT_DIRECTORIES = ("src", "tests", "docs", "data", "experiments/configs")


def create_artifact_archive(root: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite: {output}")
    accepted_manifest = root / "experiments" / "accepted-runs.json"
    runs_root = root / "experiments" / "runs"
    if not verify_run_set(runs_root, accepted_manifest):
        raise ValueError("accepted experiment runs failed verification")
    accepted = json.loads(accepted_manifest.read_text(encoding="utf-8"))[
        "accepted_runs"
    ]
    paths = [root / name for name in ROOT_FILES]
    for directory in ROOT_DIRECTORIES:
        paths.extend(_files(root / directory))
    paths.append(accepted_manifest)
    for run_id in accepted:
        paths.extend(_files(runs_root / run_id))
    files = tuple(sorted(set(paths), key=lambda path: str(path.relative_to(root))))
    if any(not path.is_file() or path.is_symlink() for path in files):
        raise ValueError("artifact inputs must be regular files")
    file_hashes = {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "redistribution_status": "permitted_under_apache_2_0",
        "accepted_runs": accepted,
        "files": file_hashes,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                for path in files:
                    _add_bytes(tar, str(path.relative_to(root)), path.read_bytes())
                _add_bytes(
                    tar,
                    "ARTIFACT-MANIFEST.json",
                    (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
                )
    return manifest


def _gzip_envelope_intact(archive: Path) -> bool:
    """Decode the whole gzip stream so its trailing CRC is actually checked.

    Verifying member checksums alone only proves *content* integrity: a byte
    flipped in tar padding or gzip framing can leave every member unchanged and
    pass. Reading the stream to completion forces gzip's CRC32/length check, so
    envelope corruption is reported rather than silently accepted.
    """
    try:
        with gzip.open(archive, "rb") as stream:
            while stream.read(1 << 20):
                pass
    except (OSError, EOFError, zlib.error):
        return False
    return True


def verify_artifact_archive(archive: Path) -> bool:
    if not _gzip_envelope_intact(archive):
        return False
    try:
        with tarfile.open(archive, mode="r:gz") as tar:
            members = tar.getmembers()
            if any(not member.isfile() for member in members):
                return False
            names = [member.name for member in members]
            if len(names) != len(set(names)) or "ARTIFACT-MANIFEST.json" not in names:
                return False
            manifest_file = tar.extractfile("ARTIFACT-MANIFEST.json")
            if manifest_file is None:
                return False
            manifest = json.loads(manifest_file.read())
            recorded = manifest["files"]
            actual = {}
            for name in names:
                if name == "ARTIFACT-MANIFEST.json":
                    continue
                stream = tar.extractfile(name)
                if stream is None:
                    return False
                actual[name] = hashlib.sha256(stream.read()).hexdigest()
            return recorded == actual
    except (KeyError, OSError, tarfile.TarError, json.JSONDecodeError):
        return False


def _files(directory: Path) -> list[Path]:
    return [path for path in directory.rglob("*") if path.is_file()]


def _add_bytes(tar: tarfile.TarFile, name: str, payload: bytes) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mtime = 0
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    tar.addfile(info, io.BytesIO(payload))
