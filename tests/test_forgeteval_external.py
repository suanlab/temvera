import subprocess
from pathlib import Path

import pytest

from temvera.forgeteval_external import run_forgeteval


def _fixture_repo(root: Path) -> str:
    generator = root / "bench" / "forgeteval" / "generate.py"
    generator.parent.mkdir(parents=True)
    generator.write_text(
        """
from dataclasses import dataclass
@dataclass
class Case:
    id: str = "case-1"
    family: str = "purge"
    def run(self, adapter):
        adapter.reset(); adapter.inscribe("secret alpha")
        return adapter.purge("secret alpha") == 1
def generate(scale, seed, distractors):
    return [Case() for _ in range(scale)]
""".lstrip(),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_external_runner_pins_source_and_refuses_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source"
    commit = _fixture_repo(source)
    output = tmp_path / "run"
    metrics = run_forgeteval(
        source,
        output,
        expected_commit=commit,
        scale=2,
        seed=42,
        distractors=4,
    )
    assert metrics["passed"] == 2
    assert (output / "checksums.json").is_file()
    with pytest.raises(FileExistsError):
        run_forgeteval(
            source,
            output,
            expected_commit=commit,
            scale=2,
            seed=42,
            distractors=4,
        )


def test_external_runner_rejects_wrong_commit(tmp_path: Path) -> None:
    source = tmp_path / "source"
    _fixture_repo(source)
    with pytest.raises(ValueError, match="source commit mismatch"):
        run_forgeteval(
            source,
            tmp_path / "run",
            expected_commit="0" * 40,
            scale=1,
            seed=1,
            distractors=0,
        )
