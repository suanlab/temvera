from pathlib import Path

import pytest

from temvera.literature import freeze_review, verify_review_freeze


def _review_fixture(root: Path) -> tuple[Path, Path]:
    review = root / "data" / "literature"
    review.mkdir(parents=True)
    (review / "studies.csv").write_text(
        "study_id,evidence_ids,review_state\nA,E-001,single_screened\n",
        encoding="utf-8",
    )
    (review / "search-log.csv").write_text(
        "search_id,query\nS1,memory\n", encoding="utf-8"
    )
    (review / "exclusions.csv").write_text(
        "exclusion_id,reason\nX1,survey\n", encoding="utf-8"
    )
    (review / "rescreen-log.csv").write_text(
        "study_id,decision\nA,include\n", encoding="utf-8"
    )
    ledger = root / "docs" / "evidence-ledger.md"
    ledger.parent.mkdir()
    ledger.write_text("| E-001 | claim |\n", encoding="utf-8")
    return review, ledger


def test_review_freeze_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    review, ledger = _review_fixture(tmp_path)
    manifest_path = review / "review-freeze.json"
    manifest = freeze_review(review, ledger, manifest_path)
    assert manifest["rescreen_sample_ids"] == ["A"]
    assert manifest["rescreened_ids"] == ["A"]
    assert verify_review_freeze(review, ledger, manifest_path)
    with pytest.raises(FileExistsError):
        freeze_review(review, ledger, manifest_path)
    (review / "studies.csv").write_text(
        "study_id,evidence_ids,review_state\nA,E-001,dual_screened\n",
        encoding="utf-8",
    )
    assert not verify_review_freeze(review, ledger, manifest_path)


def test_review_freeze_detects_rescreen_log_changes(tmp_path: Path) -> None:
    review, ledger = _review_fixture(tmp_path)
    manifest_path = review / "review-freeze.json"
    freeze_review(review, ledger, manifest_path)
    (review / "rescreen-log.csv").write_text(
        "study_id,decision\nA,exclude\n", encoding="utf-8"
    )
    assert not verify_review_freeze(review, ledger, manifest_path)


def test_review_freeze_rejects_unknown_ledger_id(tmp_path: Path) -> None:
    review, ledger = _review_fixture(tmp_path)
    (review / "studies.csv").write_text(
        "study_id,evidence_ids,review_state\nA,E-999,single_screened\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        freeze_review(review, ledger, review / "review-freeze.json")


def test_review_freeze_rejects_duplicate_identifiers(tmp_path: Path) -> None:
    review, ledger = _review_fixture(tmp_path)
    (review / "search-log.csv").write_text(
        "search_id,query\nS1,a\nS1,b\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate search_id"):
        freeze_review(review, ledger, review / "review-freeze.json")
