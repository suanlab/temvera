"""Deterministic provenance checks and deletion-lineage planning."""

from __future__ import annotations

from dataclasses import dataclass

from .model import Authority, Belief


AUTHORITY_RANK = {
    Authority.INFERRED: 0,
    Authority.EXTERNAL: 1,
    Authority.USER: 2,
    Authority.VERIFIED_TOOL: 3,
    Authority.SYSTEM: 4,
}


@dataclass(frozen=True, slots=True)
class ActionDecision:
    allowed: bool
    reason: str
    evidence_ids: tuple[str, ...]


class ProvenanceGate:
    def __init__(self, minimum: Authority = Authority.VERIFIED_TOOL) -> None:
        self.minimum = minimum

    def evaluate(self, evidence: tuple[Belief, ...]) -> ActionDecision:
        ids = tuple(sorted(belief.belief_id for belief in evidence))
        if not evidence:
            return ActionDecision(False, "no evidence", ids)
        if any(not belief.sources for belief in evidence):
            return ActionDecision(False, "missing source provenance", ids)
        if any(
            AUTHORITY_RANK[belief.authority] < AUTHORITY_RANK[self.minimum]
            for belief in evidence
        ):
            return ActionDecision(False, "insufficient authority", ids)
        return ActionDecision(True, "authority and provenance satisfied", ids)


@dataclass(frozen=True, slots=True)
class SecurityResult:
    attacks: int
    attack_success_rate: float
    benign_utility: float


def evaluate_gate(
    gate: ProvenanceGate,
    attacks: tuple[tuple[Belief, ...], ...],
    benign: tuple[tuple[Belief, ...], ...],
) -> SecurityResult:
    if not attacks or not benign:
        raise ValueError("attack and benign fixtures must both be non-empty")
    attack_successes = sum(gate.evaluate(item).allowed for item in attacks)
    benign_allowed = sum(gate.evaluate(item).allowed for item in benign)
    return SecurityResult(
        attacks=len(attacks),
        attack_success_rate=attack_successes / len(attacks),
        benign_utility=benign_allowed / len(benign),
    )


def laundering_detected(belief: Belief, ancestors: dict[str, Belief]) -> bool:
    """High-authority derivatives cannot erase lower-authority ancestry."""
    own_rank = AUTHORITY_RANK[belief.authority]
    pending = list(belief.derived_from)
    seen: set[str] = set()
    while pending:
        ancestor_id = pending.pop()
        if ancestor_id in seen:
            continue
        seen.add(ancestor_id)
        ancestor = ancestors.get(ancestor_id)
        if ancestor is None:
            return True
        if AUTHORITY_RANK[ancestor.authority] < own_rank:
            return True
        pending.extend(ancestor.derived_from)
    return False
