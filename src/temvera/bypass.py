"""Adaptive governance bypass probes, including expected trust-root failure."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from .governance import GovernedMemoryPolicy, sign_envelope
from .model import Authority, Belief


@dataclass(frozen=True, slots=True)
class BypassResult:
    probe: str
    activated: bool
    expected_limitation: bool


def run_bypass_probes() -> tuple[BypassResult, ...]:
    now = datetime(2025, 1, 1, tzinfo=timezone.utc)
    private = Ed25519PrivateKey.from_private_bytes(b"T" * 32)
    policy = GovernedMemoryPolicy({"tool-a": private.public_key()})
    trusted = _belief("trusted", now)
    signed = sign_envelope(trusted, "tenant-a", "tool-a", private)

    compromised = replace(trusted, belief_id="compromised", value="malicious")
    compromised_signed = sign_envelope(
        compromised, "tenant-a", "tool-a", private
    )
    compromised_allowed = policy.authorize_action(
        (compromised_signed,), tenant="tenant-a", at=now
    ).allowed

    cross_tenant = replace(signed, tenant="tenant-b")
    cross_allowed = policy.authorize_action(
        (cross_tenant,), tenant="tenant-a", at=now
    ).allowed

    tampered = replace(signed, belief=replace(trusted, value="tampered"))
    tampered_allowed = policy.authorize_action(
        (tampered,), tenant="tenant-a", at=now
    ).allowed

    expired_belief = replace(trusted, valid_to=now + timedelta(hours=1))
    expired = sign_envelope(expired_belief, "tenant-a", "tool-a", private)
    expired_allowed = policy.authorize_action(
        (expired,), tenant="tenant-a", at=now + timedelta(hours=2)
    ).allowed
    return (
        BypassResult("compromised_trusted_signer", compromised_allowed, True),
        BypassResult("cross_tenant_replay", cross_allowed, False),
        BypassResult("signed_claim_tamper", tampered_allowed, False),
        BypassResult("expired_signature_replay", expired_allowed, False),
    )


def _belief(belief_id: str, now: datetime) -> Belief:
    return Belief(
        belief_id,
        "payment",
        "destination",
        "approved",
        now,
        None,
        now,
        now,
        Authority.VERIFIED_TOOL,
        ("tool:signed",),
        (),
    )
