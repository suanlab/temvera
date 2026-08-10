import pytest

from temvera.audit_study import (
    crossover_assignments,
    generate_audit_tasks,
    score_audit_response,
)


def test_audit_tasks_are_seeded_and_assignments_are_balanced() -> None:
    tasks = generate_audit_tasks(17, count=12)
    assert tasks == generate_audit_tasks(17, count=12)
    assignments = crossover_assignments(("p001", "p002"), tasks)
    for code in ("p001", "p002"):
        conditions = [row.condition for row in assignments if row.participant_code == code]
        assert conditions.count("provenance_diff") == 6
        assert conditions.count("opaque_current_state") == 6


def test_audit_response_scores_detection_correction_and_side_effects() -> None:
    task = generate_audit_tasks(3, count=1)[0]
    score = score_audit_response(
        task,
        reported_fault=True,
        submitted_value=task.expected_value,
        edited_fields=(f"{task.subject}.{task.attribute}", "entity-999.city"),
        elapsed_seconds=12.5,
    )
    assert score.detected and score.corrected
    assert score.unintended_edits == 1


def test_audit_study_rejects_invalid_design_inputs() -> None:
    with pytest.raises(ValueError):
        generate_audit_tasks(1, count=0)
    task = generate_audit_tasks(1, count=1)[0]
    with pytest.raises(ValueError):
        crossover_assignments(("same", "same"), (task,))
    with pytest.raises(ValueError):
        score_audit_response(
            task,
            reported_fault=False,
            submitted_value="",
            edited_fields=(),
            elapsed_seconds=-1,
        )
