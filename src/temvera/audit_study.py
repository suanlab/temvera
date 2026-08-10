"""Deterministic task generation and scoring for the planned audit study."""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuditTask:
    task_id: str
    subject: str
    attribute: str
    expected_value: str
    planted_value: str
    fault_type: str


@dataclass(frozen=True, slots=True)
class Assignment:
    participant_code: str
    task_id: str
    condition: str
    order: int


@dataclass(frozen=True, slots=True)
class AuditScore:
    detected: bool
    corrected: bool
    unintended_edits: int
    elapsed_seconds: float


def generate_audit_tasks(seed: int, count: int = 12) -> tuple[AuditTask, ...]:
    if count <= 0:
        raise ValueError("count must be positive")
    rng = random.Random(seed)
    attributes = ("employer", "city", "access", "diet")
    values = {
        "employer": ("Atlas", "Beacon"),
        "city": ("Busan", "Seoul"),
        "access": ("reader", "admin"),
        "diet": ("vegan", "pescatarian"),
    }
    fault_types = ("stale_value", "wrong_subject", "missing_provenance")
    tasks = []
    for index in range(count):
        attribute = attributes[index % len(attributes)]
        expected, planted = values[attribute]
        nonce = rng.getrandbits(32)
        task_id = hashlib.sha256(f"{seed}:{index}:{nonce}".encode()).hexdigest()[:12]
        tasks.append(
            AuditTask(
                task_id=task_id,
                subject=f"entity-{index:03d}",
                attribute=attribute,
                expected_value=expected,
                planted_value=planted,
                fault_type=fault_types[index % len(fault_types)],
            )
        )
    return tuple(tasks)


def crossover_assignments(
    participant_codes: tuple[str, ...], tasks: tuple[AuditTask, ...]
) -> tuple[Assignment, ...]:
    if not participant_codes or not tasks:
        raise ValueError("participants and tasks must be non-empty")
    if len(set(participant_codes)) != len(participant_codes):
        raise ValueError("participant codes must be unique")
    rows = []
    for participant_index, code in enumerate(participant_codes):
        for order, task in enumerate(tasks, start=1):
            condition = (
                "provenance_diff"
                if (participant_index + order) % 2 == 0
                else "opaque_current_state"
            )
            rows.append(Assignment(code, task.task_id, condition, order))
    return tuple(rows)


def score_audit_response(
    task: AuditTask,
    *,
    reported_fault: bool,
    submitted_value: str,
    edited_fields: tuple[str, ...],
    elapsed_seconds: float,
) -> AuditScore:
    if elapsed_seconds < 0:
        raise ValueError("elapsed_seconds must be non-negative")
    allowed_edit = f"{task.subject}.{task.attribute}"
    return AuditScore(
        detected=reported_fault,
        corrected=submitted_value == task.expected_value,
        unintended_edits=sum(field != allowed_edit for field in edited_fields),
        elapsed_seconds=elapsed_seconds,
    )
