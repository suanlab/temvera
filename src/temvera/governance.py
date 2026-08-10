"""Signed provenance, tenant scoping, and separate ingest/action policies."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Mapping

from .model import Authority, Belief
from .security import AUTHORITY_RANK, ActionDecision, laundering_detected


@dataclass(frozen=True, slots=True)
class EvidenceEnvelope:
    belief: Belief
    tenant: str
    principal: str
    signature: bytes | None = None


@dataclass(frozen=True, slots=True)
class IngestDecision:
    accepted: bool
    quarantined: bool
    reason: str


def sign_envelope(
    belief: Belief, tenant: str, principal: str, private_key: object
) -> EvidenceEnvelope:
    signature = private_key.sign(_signing_bytes(belief, tenant, principal))
    return EvidenceEnvelope(belief, tenant, principal, signature)


def verify_envelope(
    envelope: EvidenceEnvelope, public_keys: Mapping[str, object]
) -> bool:
    public_key = public_keys.get(envelope.principal)
    if public_key is None or envelope.signature is None:
        return False
    try:
        public_key.verify(
            envelope.signature,
            _signing_bytes(envelope.belief, envelope.tenant, envelope.principal),
        )
    except Exception:
        return False
    return True


class GovernedMemoryPolicy:
    def __init__(self, public_keys: Mapping[str, object]) -> None:
        self.public_keys = public_keys

    def ingest(self, envelope: EvidenceEnvelope) -> IngestDecision:
        requires_signature = envelope.belief.authority in {
            Authority.SYSTEM,
            Authority.VERIFIED_TOOL,
        }
        if requires_signature and not verify_envelope(envelope, self.public_keys):
            return IngestDecision(False, False, "unverified high-authority claim")
        quarantined = AUTHORITY_RANK[envelope.belief.authority] < AUTHORITY_RANK[
            Authority.VERIFIED_TOOL
        ]
        return IngestDecision(True, quarantined, "accepted as data")

    def authorize_action(
        self,
        envelopes: tuple[EvidenceEnvelope, ...],
        *,
        tenant: str,
        at: datetime,
        ancestors: Mapping[str, Belief] | None = None,
    ) -> ActionDecision:
        ids = tuple(sorted(item.belief.belief_id for item in envelopes))
        if not envelopes:
            return ActionDecision(False, "no evidence", ids)
        if any(item.tenant != tenant for item in envelopes):
            return ActionDecision(False, "cross-tenant evidence", ids)
        if any(not item.belief.valid_at(at) for item in envelopes):
            return ActionDecision(False, "evidence not valid at action time", ids)
        if any(not item.belief.sources for item in envelopes):
            return ActionDecision(False, "missing source provenance", ids)
        if any(
            AUTHORITY_RANK[item.belief.authority]
            < AUTHORITY_RANK[Authority.VERIFIED_TOOL]
            for item in envelopes
        ):
            return ActionDecision(False, "insufficient authority", ids)
        if any(not verify_envelope(item, self.public_keys) for item in envelopes):
            return ActionDecision(False, "invalid signature", ids)
        ancestry = dict(ancestors or {})
        if any(laundering_detected(item.belief, ancestry) for item in envelopes):
            return ActionDecision(False, "untrusted derivation lineage", ids)
        return ActionDecision(True, "governance checks satisfied", ids)


def public_key_fingerprint(public_key: object) -> str:
    from cryptography.hazmat.primitives import serialization

    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return hashlib.sha256(raw).hexdigest()


def _signing_bytes(belief: Belief, tenant: str, principal: str) -> bytes:
    data = asdict(belief)
    for key in ("valid_from", "valid_to", "recorded_at", "last_confirmed_at"):
        value = data[key]
        data[key] = value.isoformat() if value else None
    data["authority"] = belief.authority.value
    envelope = {"belief": data, "principal": principal, "tenant": tenant}
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()
