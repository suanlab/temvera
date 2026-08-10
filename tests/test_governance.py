from dataclasses import replace
from datetime import datetime, timezone
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from temvera.governance import (
    EvidenceEnvelope,
    GovernedMemoryPolicy,
    public_key_fingerprint,
    sign_envelope,
    verify_envelope,
)
from temvera.model import Authority, Belief


NOW = datetime(2025, 1, 1, tzinfo=timezone.utc)


def belief(
    belief_id: str = "b",
    authority: Authority = Authority.VERIFIED_TOOL,
    derived_from: tuple[str, ...] = (),
) -> Belief:
    return Belief(
        belief_id,
        "subject",
        "attribute",
        "value",
        NOW,
        None,
        NOW,
        NOW,
        authority,
        ("source",),
        derived_from,
    )


class GovernanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.private = Ed25519PrivateKey.generate()
        self.public = self.private.public_key()
        self.policy = GovernedMemoryPolicy({"tool-a": self.public})

    def test_signature_binds_belief_tenant_and_principal(self) -> None:
        envelope = sign_envelope(belief(), "tenant-a", "tool-a", self.private)
        self.assertTrue(verify_envelope(envelope, {"tool-a": self.public}))
        tampered = replace(envelope, tenant="tenant-b")
        self.assertFalse(verify_envelope(tampered, {"tool-a": self.public}))
        self.assertEqual(len(public_key_fingerprint(self.public)), 64)

    def test_ingest_quarantines_external_and_rejects_forged_authority(self) -> None:
        external = EvidenceEnvelope(
            belief(authority=Authority.EXTERNAL), "tenant-a", "web"
        )
        forged = EvidenceEnvelope(belief(), "tenant-a", "tool-a")
        external_decision = self.policy.ingest(external)
        self.assertTrue(external_decision.accepted)
        self.assertTrue(external_decision.quarantined)
        self.assertFalse(self.policy.ingest(forged).accepted)

    def test_action_rejects_cross_tenant_forgery_and_laundering(self) -> None:
        signed = sign_envelope(belief(), "tenant-a", "tool-a", self.private)
        self.assertTrue(
            self.policy.authorize_action((signed,), tenant="tenant-a", at=NOW).allowed
        )
        self.assertFalse(
            self.policy.authorize_action((signed,), tenant="tenant-b", at=NOW).allowed
        )
        tampered = replace(signed, belief=replace(signed.belief, value="tampered"))
        self.assertFalse(
            self.policy.authorize_action((tampered,), tenant="tenant-a", at=NOW).allowed
        )
        ancestor = belief("ancestor", Authority.EXTERNAL)
        derived = belief("derived", derived_from=("ancestor",))
        signed_derived = sign_envelope(
            derived, "tenant-a", "tool-a", self.private
        )
        decision = self.policy.authorize_action(
            (signed_derived,),
            tenant="tenant-a",
            at=NOW,
            ancestors={"ancestor": ancestor},
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "untrusted derivation lineage")

    def test_expired_signed_evidence_is_rejected_at_action_time(self) -> None:
        from datetime import timedelta

        expired = replace(belief(), valid_to=NOW + timedelta(days=1))
        signed = sign_envelope(expired, "tenant-a", "tool-a", self.private)
        decision = self.policy.authorize_action(
            (signed,), tenant="tenant-a", at=NOW + timedelta(days=2)
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "evidence not valid at action time")


if __name__ == "__main__":
    unittest.main()
