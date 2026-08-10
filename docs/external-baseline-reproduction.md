# External Baseline Reproduction Record

## Springdrift experiment 5

- Source: `seamus-brady/springdrift`
- Commit: `19b52b9c794dd5cdfaa5e6d9efba0dfa8049dc01`
- License: AGPL-3.0-or-later
- Command: `python3 evals/experiment-5/run_eval.py`
- Date: 2026-07-16

The command completed twice in an environment without Ollama. Both runs
produced identical fallback artifacts:

- `experiment5_results.json`: `b21cf7ebe47c546f8718da547009c25ca8546d9a86f0bcfc904aa57ebd1b10e7`
- `learning_curve.csv`: `933776f9dbb469df2138e349d176a4dfede6487c82c5e6bc8bcae0eb8a9aae2d`

This is not an end-to-end system reproduction. The script catches embedding
request failures and substitutes 768-dimensional zero vectors. Its retrieval
point estimates consequently differ from the committed results without
marking the run invalid. The confidence-decay checks passed, but the script
reimplements the equation rather than importing the production Gleam
function. Full runtime execution additionally requires Gleam/Erlang and an LLM
provider credential, neither available in the verification environment.

No Springdrift source or generated output is redistributed in this repository.

## Springdrift experiment 2

The documented `generate_cases_v2.py` and `run_eval.py` path was attempted at
the same pinned commit. Although the evaluation README labels experiment 2
“deterministic only,” `run_eval.py` still requests `nomic-embed-text` from
Ollama for its RAG arm and emits one connection failure per item when Ollama is
absent. The run was terminated before completion during the subsequent Python
CBR calculation; it produced no accepted result. This failed attempt is not a
baseline score and reinforces the requirement to pin the embedding service and
to fail closed rather than silently substitute vectors.
