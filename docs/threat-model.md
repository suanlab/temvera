# Memory provenance threat model

## Protected decision

The initial mechanism-isolation harness protects dispatch of a sensitive action
whose justification contains retrieved memory. It does not claim to secure the
LLM, host, Git repository, model provider, or arbitrary tool implementations.

## Adversary and attacks

The adversary may submit untrusted conversation or web content and attempt to
make it persist. It cannot forge an external signature or directly modify the
trusted policy. The deterministic suite covers:

- query-only injection written with `external` authority;
- forged front matter claiming high authority but lacking a source;
- provenance laundering where a trusted-looking derived item descends from an
  untrusted ancestor;
- a signed benign tool result used to measure utility loss.

Fixture values are inert labels and never contain executable instructions.

## Security properties and metrics

The action gate requires complete source references, sufficient authority, and
no lower-authority derivation ancestry. Report write acceptance separately from
downstream action success. The smoke report measures attack success rate (ASR),
benign utility, and detected laundering. A zero smoke-test ASR is only a unit
property of these fixtures, not evidence of real-world security.

The governed profile additionally binds an Ed25519 signature to the complete
belief, tenant, and principal. External evidence may be accepted in quarantine
while remaining ineligible for sensitive actions. High-authority claims without
a valid configured signature are rejected at ingestion; valid evidence from a
different tenant is rejected at action time.

## Out of scope and required extensions

Cross-tenant isolation, signature verification, compromised trusted tools,
indirect multi-turn attacks, parser differentials, Git-history erasure, and
adaptive bypasses remain outside v0. Before a security claim, reproduce MINJA
and MemLineage-compatible workloads, add model-mediated trials, and report
confidence intervals and bypass analysis.

The initial adaptive probes now cover cross-tenant replay, payload tampering,
expiry replay, and a compromised trusted signer. The last probe succeeds by
design and defines the trust-root boundary. Key revocation, signer compromise
detection, and multi-party approval remain required extensions.
