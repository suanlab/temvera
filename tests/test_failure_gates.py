"""An infrastructure failure must stop a run, never become a score (CHECK.md F03).

A failed ingest reads as a lost memory, a failed delete as a kept one, a failed
request as an empty answer, and a failed reset leaves an earlier run's data in
the store. These inject each failure into the code that guards against it."""

from __future__ import annotations

import pytest

from temvera.cli import require_clean
from temvera.hindsight_adapter import HindsightSystem, HindsightUnavailable
from temvera.mem0_adapter import Mem0System


def test_a_run_with_worker_errors_is_not_sealed() -> None:
    with pytest.raises(SystemExit, match="refusing to seal: 2 worker errors"):
        require_clean({"backbone": {"worker_errors": 2, "worker_error_messages": ["HTTP 500"]}}, {})


def test_only_a_run_meant_to_study_errors_may_keep_them() -> None:
    require_clean({"backbone": {"worker_errors": 2}}, {"allow_worker_errors": True})
    require_clean({"backbone": {"worker_errors": 0}}, {})
    require_clean({"backbone": {}}, {})


class _Memory:
    def __init__(self, rows: list, fail_delete: bool = False) -> None:
        self.rows, self.fail_delete = rows, fail_delete

    def delete_all(self, user_id: str) -> None:
        if self.fail_delete:
            raise RuntimeError("store unavailable")
        self.rows = []

    def get_all(self, user_id: str) -> dict:
        return {"results": self.rows}


def _mem0(memory: _Memory) -> Mem0System:
    system = object.__new__(Mem0System)
    system._memory, system._user_id = memory, "u"
    return system


def test_mem0_reset_accepts_an_empty_store_and_rejects_a_failed_one() -> None:
    _mem0(_Memory([{"memory": "x"}])).reset()
    _mem0(_Memory([], fail_delete=True)).reset()  # nothing to delete: not a failure
    with pytest.raises(RuntimeError, match="left 1 memories"):
        _mem0(_Memory([{"memory": "x"}], fail_delete=True)).reset()


def _hindsight(code: int) -> HindsightSystem:
    system = HindsightSystem(base_url="http://localhost:1", bank="b")

    def delete(path: str) -> None:
        system._record(f"DELETE {path}: HTTP {code}: body")

    system._delete = delete
    return system


def test_hindsight_reset_accepts_a_missing_bank_only() -> None:
    system = _hindsight(404)
    system.reset()
    assert system.worker_errors == 0
    with pytest.raises(HindsightUnavailable, match="HTTP 500"):
        _hindsight(500).reset()


class _Bank:
    def __init__(self, models: list[str]) -> None:
        self.models = models

    def models_used(self, psql: str, instance: dict) -> list[str]:
        return self.models


def test_hindsight_runs_stop_on_a_model_the_config_did_not_name(tmp_path, monkeypatch) -> None:
    from temvera.external_experiment import hindsight_receipt

    instance = tmp_path / "instance.json"
    instance.write_text('{"port": 1, "username": "u", "database": "d", "password": "p"}')
    monkeypatch.setenv("HINDSIGHT_PSQL", "psql")
    monkeypatch.setenv("HINDSIGHT_PG_INSTANCE", str(instance))
    assert hindsight_receipt({"model": "gpt-4o-mini"}, [_Bank(["gpt-4o-mini"])]) == ["gpt-4o-mini"]
    with pytest.raises(SystemExit, match="daemon used"):
        hindsight_receipt({"model": "gpt-4o"}, [_Bank(["gpt-4o-mini"])])
    monkeypatch.delenv("HINDSIGHT_PSQL")
    with pytest.raises(SystemExit, match="HINDSIGHT_PSQL"):
        hindsight_receipt({"model": "gpt-4o"}, [_Bank([])])
    assert hindsight_receipt({"model_check": "skip"}, []).startswith("not checked")
