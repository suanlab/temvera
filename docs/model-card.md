# Model Card and Applicability Statement

## Primary artifact

No learned model is trained, fine-tuned, or distributed. The accepted lifecycle,
decay, retrieval-mechanism, governance, and ForgetEval lexical studies are
deterministic or use dependency-free hashing/lexical methods. Consequently a
conventional model card is not applicable to the primary artifact.

## Optional learned component

`temvera.learned` can evaluate a FastEmbed model selected in
`experiments/configs/learned-vector.json`. That evaluation was not completed,
its model was not downloaded under scope decision D-009, and no learned-vector
result is accepted or reported. Model identity, revision, license, file checksums, embedding
dimension, and download provenance must be recorded before future use.

## Responsible-use boundary

The repository is a research harness, not a production memory service. The
synthetic results do not establish factual reliability, privacy compliance,
secure deletion across undeclared replicas, or resistance to adaptive attacks.
No private conversations, secrets, or licensed third-party datasets are
included in the accepted artifact.
