import json

import pytest

from temvera.experiment import verify_run
from temvera.security_experiment import run_security_experiment


def test_security_experiment_is_sealed_and_preserves_expected_bypass(tmp_path) -> None:
    output = tmp_path / "run"
    run_security_experiment({"seed": 17}, output)
    assert verify_run(output)
    results = json.loads((output / "results.json").read_text())
    assert results["undefended"]["attack_success_rate"] == 1.0
    assert results["governed"]["attack_activation_rate"] == 0.0
    activated = [row for row in results["adaptive_bypass"] if row["activated"]]
    assert [row["probe"] for row in activated] == ["compromised_trusted_signer"]
    with pytest.raises(FileExistsError):
        run_security_experiment({"seed": 17}, output)
