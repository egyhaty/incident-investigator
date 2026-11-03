# Evaluation and honest claims

There are three different kinds of evidence in this project:

1. **Software tests** verify retrieval, policy gates, bounded execution, HTTP behavior, and the Ollama protocol adapter using a local stub.
2. **Demo regression cases** verify the deterministic reference policy on a tiny labeled dataset. They do not measure model reasoning.
3. **Live model evaluations** run the actual installed model on the same cases and record provider/model identity, diagnoses, source selection, evidence references, token counts, latency, and errors.

Run `python3 scripts/evaluate.py --output artifacts/demo-evaluation.json` for the reference baseline. Run with `--provider ollama --model YOUR_INSTALLED_MODEL` to measure an actual model. Do not present demo results as a live-model score.

The four cases are development examples, not held-out data or a statistically meaningful benchmark. They do not establish production readiness. A future evaluation should include multiple paraphrases, withheld incidents, healthy counterexamples, conflicting signals, missing telemetry, malicious documents, and repeated runs per model.

Current checks include expected diagnosis, presence of a relevant runbook source, required critical evidence, and no executed mutations. Sentence-level grounding, quality of proposed next steps, retrieval recall at scale, and adversarial robustness are not comprehensively evaluated.

Abstention is a first-class expected result. Exit code 137 without OOMKilled is tested as insufficient evidence. Multiple replies from the same MAC are not treated as two distinct address owners.

Tool-call attempts outside the allowlist are blocked even if the model or an injected document requests them. This demonstrates a narrow capability boundary; it does not prove complete prompt-injection resistance.
