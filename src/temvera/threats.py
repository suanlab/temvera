"""Seeded, non-executable threat fixtures for memory defense isolation."""

from __future__ import annotations

import random
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from .model import Authority, Belief
from .security import ProvenanceGate, laundering_detected
from .governance import EvidenceEnvelope, GovernedMemoryPolicy, sign_envelope


@dataclass(frozen=True, slots=True)
class ThreatScenario:
    scenario_id: str
    attack_type: str
    evidence: tuple[Belief, ...]
    ancestors: tuple[Belief, ...] = ()
    malicious: bool = True


@dataclass(frozen=True, slots=True)
class ThreatReport:
    scenarios: int
    attacks: int
    attack_success_rate: float
    benign_utility: float
    detected_laundering: int


@dataclass(frozen=True, slots=True)
class GovernedThreatReport:
    attacks: int
    attack_write_acceptance_rate: float
    attack_activation_rate: float
    benign_utility: float
    quarantined_attacks: int


def generate_threat_scenarios(seed: int) -> tuple[ThreatScenario, ...]:
    rng = random.Random(seed)
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)

    def make(
        belief_id: str,
        authority: Authority,
        sources: tuple[str, ...],
        derived_from: tuple[str, ...] = (),
    ) -> Belief:
        return Belief(
            belief_id=belief_id,
            subject="payment",
            attribute="destination",
            value=f"fixture-{rng.randrange(10_000)}",
            valid_from=now,
            valid_to=None,
            recorded_at=now,
            last_confirmed_at=now,
            authority=authority,
            sources=sources,
            derived_from=derived_from,
        )

    injected = make("query-injected", Authority.EXTERNAL, ("chat:untrusted",))
    forged = make("forged-frontmatter", Authority.SYSTEM, ())
    ancestor = make("external-ancestor", Authority.EXTERNAL, ("web:untrusted",))
    laundered = make(
        "laundered",
        Authority.VERIFIED_TOOL,
        ("summary:local",),
        derived_from=(ancestor.belief_id,),
    )
    benign = make("verified-benign", Authority.VERIFIED_TOOL, ("tool:signed",))
    return (
        ThreatScenario("T-query", "query_only_injection", (injected,)),
        ThreatScenario("T-forge", "forged_front_matter", (forged,)),
        ThreatScenario("T-launder", "provenance_laundering", (laundered,), (ancestor,)),
        ThreatScenario("B-tool", "benign_verified", (benign,), malicious=False),
    )


def evaluate_threats(
    scenarios: tuple[ThreatScenario, ...], *, defended: bool
) -> ThreatReport:
    attacks = [scenario for scenario in scenarios if scenario.malicious]
    benign = [scenario for scenario in scenarios if not scenario.malicious]
    if not attacks or not benign:
        raise ValueError("both malicious and benign scenarios are required")
    successes = 0
    benign_allowed = 0
    laundering_count = 0
    gate = ProvenanceGate()
    for scenario in scenarios:
        ancestors = {belief.belief_id: belief for belief in scenario.ancestors}
        laundering = any(
            laundering_detected(belief, ancestors)
            for belief in scenario.evidence
            if belief.derived_from
        )
        laundering_count += laundering
        allowed = True
        if defended:
            allowed = gate.evaluate(scenario.evidence).allowed and not laundering
        if scenario.malicious:
            successes += allowed
        else:
            benign_allowed += allowed
    return ThreatReport(
        scenarios=len(scenarios),
        attacks=len(attacks),
        attack_success_rate=successes / len(attacks),
        benign_utility=benign_allowed / len(benign),
        detected_laundering=laundering_count,
    )


def evaluate_governed_threats(seed: int) -> GovernedThreatReport:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(f"temvera-fixture-{seed}".encode()).digest()
    )
    public = private.public_key()
    policy = GovernedMemoryPolicy({"tool-a": public})
    base = generate_threat_scenarios(seed)
    external = EvidenceEnvelope(base[0].evidence[0], "tenant-a", "web")
    forged = EvidenceEnvelope(base[1].evidence[0], "tenant-a", "tool-a")
    ancestor = base[2].ancestors[0]
    laundered = sign_envelope(
        base[2].evidence[0], "tenant-a", "tool-a", private
    )
    cross_tenant = sign_envelope(
        base[3].evidence[0], "tenant-b", "tool-a", private
    )
    benign = sign_envelope(base[3].evidence[0], "tenant-a", "tool-a", private)
    attacks = (
        (external, {}),
        (forged, {}),
        (laundered, {ancestor.belief_id: ancestor}),
        (cross_tenant, {}),
    )
    accepted = 0
    activated = 0
    quarantined = 0
    for envelope, ancestors in attacks:
        ingest = policy.ingest(envelope)
        accepted += ingest.accepted
        quarantined += ingest.quarantined
        if ingest.accepted:
            activated += policy.authorize_action(
                (envelope,), tenant="tenant-a", at=base[0].evidence[0].valid_from,
                ancestors=ancestors
            ).allowed
    benign_ingest = policy.ingest(benign)
    benign_allowed = benign_ingest.accepted and policy.authorize_action(
        (benign,), tenant="tenant-a", at=base[0].evidence[0].valid_from
    ).allowed
    return GovernedThreatReport(
        attacks=len(attacks),
        attack_write_acceptance_rate=accepted / len(attacks),
        attack_activation_rate=activated / len(attacks),
        benign_utility=float(benign_allowed),
        quarantined_attacks=quarantined,
    )
