import pytest

from temvera.generator import generate_histories
from temvera.lifecycle_grid import run_lifecycle_grid, run_operation_suite
from temvera.model import Operation


CONFIG = {
    "seeds": [1, 2, 3],
    "entities": [2],
    "revisions": [2],
    "bootstrap_samples": 50,
    "bootstrap_seed": 9,
}


def test_grid_is_deterministic_and_oracle_is_exact() -> None:
    first = run_lifecycle_grid(CONFIG)
    second = run_lifecycle_grid(CONFIG)
    assert first == second
    rows, summary = first
    assert len(rows) == 18
    oracle = summary["overall_descriptive"]["oracle"]
    assert oracle["exact_state_accuracy"]["mean"] == 1.0
    assert oracle["stale_use_rate"]["mean"] == 0.0
    condition = summary["by_condition"][
        "profile=revision_only,entities=2,revisions=2"
    ]["oracle"]
    assert condition["exact_state_accuracy"]["n_seeds"] == 3
    assert summary["by_profile_descriptive"]["revision_only"]["oracle"][
        "exact_state_accuracy"
    ]["mean"] == 1.0


@pytest.mark.parametrize(
    "override, message",
    [
        ({"seeds": [1, 2]}, "three seeds"),
        ({"entities": [0]}, "positive"),
        ({"bootstrap_samples": 0}, "bootstrap_samples"),
    ],
)
def test_grid_rejects_invalid_config(override: dict[str, object], message: str) -> None:
    config = {**CONFIG, **override}
    with pytest.raises(ValueError, match=message):
        run_lifecycle_grid(config)


def test_operation_suite_scores_empty_purged_truth() -> None:
    rows, summary = run_operation_suite(
        {"seeds": [1, 2, 3], "bootstrap_samples": 20, "bootstrap_seed": 4}
    )
    assert len(rows) == 18
    oracle = summary["overall_descriptive"]["oracle"]
    assert oracle["exact_state_accuracy"]["mean"] == 1.0
    append = summary["overall_descriptive"]["append_only"]
    assert append["exact_state_accuracy"]["mean"] < 1.0
    assert summary["by_case_category"]["oracle"]["purge"][
        "exact_state_accuracy"
    ] == 1.0
    assert summary["by_case_category"]["append_only"]["purge"][
        "exact_state_accuracy"
    ] < 1.0


def test_operation_suite_requires_three_seeds() -> None:
    with pytest.raises(ValueError, match="three seeds"):
        run_operation_suite({"seeds": [1, 2]})


def test_structural_profile_is_seeded_and_default_is_unchanged() -> None:
    default = generate_histories(seed=7, entities=5, revisions=3)
    explicit_default = generate_histories(
        seed=7,
        entities=5,
        revisions=3,
        reconfirm_probability=0.0,
        expire_probability=0.0,
        purge_probability=0.0,
    )
    mixed = generate_histories(
        seed=7,
        entities=20,
        revisions=3,
        reconfirm_probability=0.5,
        expire_probability=0.35,
        purge_probability=0.25,
    )
    assert default == explicit_default
    assert mixed == generate_histories(
        seed=7,
        entities=20,
        revisions=3,
        reconfirm_probability=0.5,
        expire_probability=0.35,
        purge_probability=0.25,
    )
    operations = {event.operation for event in mixed}
    assert {Operation.RECONFIRM, Operation.EXPIRE, Operation.PURGE} <= operations


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reconfirm_probability": -0.1},
        {"expire_probability": 1.1},
        {"expire_probability": 0.6, "purge_probability": 0.5},
    ],
)
def test_structural_profile_rejects_invalid_probabilities(
    kwargs: dict[str, float],
) -> None:
    with pytest.raises(ValueError, match="probabilit"):
        generate_histories(seed=1, **kwargs)
