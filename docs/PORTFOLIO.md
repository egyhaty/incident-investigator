# Portfolio map

## The story in one sentence

Karm DevOps builds and operates the platform; Incident Investigator explains platform incidents using bounded, evidence-first local AI.

## Why this is valuable

The combination demonstrates both sides of modern platform work:

- infrastructure delivery: Kubernetes, GitOps, networking, storage, observability, CI/CD and recovery;
- operational intelligence: tool-calling, lexical RAG, structured reports, grounding checks, abstention and model evaluation.

The second project does not claim autonomous operations. It produces a reviewable investigation and keeps mutation outside the model boundary.

## Suggested portfolio walkthrough

1. Open the Karm DevOps architecture and follow a commit through CI, image promotion and Argo CD reconciliation.
2. Show the platform's monitoring and storage/recovery surfaces.
3. Introduce an incident as the operational problem created by a platform at runtime.
4. Run the same synthetic incident in this project.
5. Inspect the tool trace, retrieved runbook sections, evidence citations and validation result.
6. Show a counterexample where the investigator abstains or fails validation.
7. Explain what would be required before connecting read-only production evidence.

## CV positioning

Use the pair as one platform-engineering narrative, with two separate project links:

> Built an on-prem Kubernetes/GitOps platform and a companion local-LLM incident investigator that retrieves runbook evidence, validates structured diagnoses, records model usage, and abstains when observations are insufficient.

Keep the measured result honest: the current instruct-model evaluation accepted 5 of 8 synthetic cases. The failures are useful evidence about citation grounding and distractor sensitivity, not something to hide.

## Design direction

The UI should feel like an incident room or operations console, not a generic AI chat template. Prefer evidence timelines, severity states, source cards, and topology over chat bubbles, purple gradients, and decorative AI effects.
