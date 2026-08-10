from datetime import datetime, timezone
import unittest

from temvera.model import Authority, Belief
from temvera.security import ProvenanceGate, evaluate_gate, laundering_detected


T0 = datetime(2025, 1, 1, tzinfo=timezone.utc)


def belief(
    belief_id: str,
    authority: Authority,
    *,
    sources: tuple[str, ...] = ("source",),
    derived_from: tuple[str, ...] = (),
) -> Belief:
    return Belief(
        belief_id,
        "subject",
        "attribute",
        "value",
        T0,
        None,
        T0,
        T0,
        authority,
        sources,
        derived_from,
    )


class SecurityTest(unittest.TestCase):
    def test_gate_rejects_external_evidence_for_sensitive_action(self) -> None:
        decision = ProvenanceGate().evaluate((belief("b", Authority.EXTERNAL),))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "insufficient authority")

    def test_gate_accepts_verified_provenance(self) -> None:
        self.assertTrue(
            ProvenanceGate().evaluate((belief("b", Authority.VERIFIED_TOOL),)).allowed
        )

    def test_missing_source_and_laundering_are_detected(self) -> None:
        untrusted = belief("u", Authority.EXTERNAL)
        promoted = belief(
            "p", Authority.VERIFIED_TOOL, derived_from=(untrusted.belief_id,)
        )
        self.assertFalse(
            ProvenanceGate().evaluate((belief("x", Authority.SYSTEM, sources=()),)).allowed
        )
        self.assertTrue(laundering_detected(promoted, {"u": untrusted}))

    def test_security_metrics_separate_attack_and_utility(self) -> None:
        result = evaluate_gate(
            ProvenanceGate(),
            attacks=((belief("attack", Authority.EXTERNAL),),),
            benign=((belief("benign", Authority.VERIFIED_TOOL),),),
        )
        self.assertEqual(result.attack_success_rate, 0.0)
        self.assertEqual(result.benign_utility, 1.0)


if __name__ == "__main__":
    unittest.main()
