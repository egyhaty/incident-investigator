# Implementation status

## Implemented

- Four synthetic scenarios, including an insufficient-evidence case.
- Six read-only fixture/retrieval tools with validated arguments.
- Local Markdown runbook retrieval using BM25 and content-derived source IDs.
- Bounded agent loop and evidence/citation gates.
- Deterministic reference demo and an optional local Ollama tool-calling adapter.
- CLI, local browser UI, JSON export, health checks, and basic Prometheus metrics.
- Unit, HTTP integration, adversarial capability, and provider-protocol tests.
- A small labeled evaluation harness with explicit distinction between demo and live inference.
- Container recipe, optional Kubernetes lab manifest, and CI workflow.

## Demonstrated on the dedicated VM

- Real local Ollama inference using `qwen3:4b-instruct-2507-q4_K_M`.
- HTTPS deployment at `investigator.murabba.net` behind Nginx.
- Basic authentication at the edge; Ollama and the application remain loopback-only.
- Eight-case evaluation with bounded validation retries: 5 / 8 accepted reports.

## Not yet demonstrated

- A public repository release of the dedicated-VM evaluation artifacts.
- Container build or Kubernetes deployment until separately validated.
- Running GitHub Actions until the repository is published and the workflow executes.
- Production authentication, durable traces, a hardened production HTTP server, or public hosting.
- Live Kubernetes/Prometheus evidence connectors, embeddings, a vector database, or multiple agents.
- Backup restoration, autonomous remediation, or a general incident root-cause guarantee.

This file should change only when new evidence supports a stronger claim.
