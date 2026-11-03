# How to explain the project

## A concrete walkthrough

Start with the duplicate-IP case. The investigator first observes a ready node and moderate resource usage. Incident events contain control-plane resets. A network tool returns two MAC addresses claiming the same IP. A runbook explains why ping can succeed during an address conflict. The report ties the diagnosis to the network observation, cites the retrieved sections, and proposes verifying interface ownership before isolating anything.

The investigator has not changed infrastructure. It has assembled a reviewable argument.

## Modules and their responsibilities

| Module | Responsibility |
|---|---|
| `agent.py` | Bounded loop, tool dispatch, trace construction, report validation |
| `tools.py` | Closed capability surface and scenario loading |
| `retrieval.py` | Section chunking, stable content IDs, BM25 ranking |
| `providers.py` | Deterministic demo and real Ollama HTTP adapter |
| `server.py` | Local UI/API, request boundaries, concurrency and metrics |
| `web/` | Scenario selection, readable evidence and tool/source inspection |
| `evals/` | Labeled expectations kept separate from runtime observations |

## Why one agent?

An investigator can already choose different tools based on observations. Splitting this into several agents would add coordination, latency, and evaluation complexity before a benefit has been demonstrated. Modules are ordinary replaceable software components; they are not automatically separate agents.

## Why retrieval rather than only prompting?

Runbooks change independently of the model. Retrieval supplies the relevant sections at investigation time and gives reviewers an exact source to inspect. The source ID changes when its text changes. The small collection currently fits lexical retrieval; embeddings would add an unmeasured dependency at this stage.

## What is enforced versus requested?

Enforced by code: tool names/arguments, no arbitrary file paths or network endpoints, no repeated tool calls, budgets, diagnosis-specific evidence gates, and references to previously retrieved sources.

Requested through instructions: treating retrieved text as data, explaining uncertainty, and proposing sensible actions. These instructions are not a security boundary. The application never executes a proposed action. Citation validation does not establish the truth of every generated sentence.

## How Hermes integrates later

Hermes can send a synthetic incident identifier to this API and consume the returned structured report. A future live evidence connector should be a separately configured boundary, with explicit user authorization, scoped read-only credentials, redaction, tests, and a private deployment. The public repository should remain independently runnable.
