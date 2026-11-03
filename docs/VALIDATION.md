# Validation record

Date: 2026-11-03. Runtime: Python 3.12 locally; dedicated Ubuntu VM for live inference.

| Check | Result | Scope |
|---|---|---|
| Python test suite | 22 tests passed | Diagnosis gates, retrieval, abstention, invalid tool calls, deadlines, budgets, API and provider protocol |
| Reference evaluation | 4 / 4 cases passed | Deterministic fixture regression only; see `demo-evaluation.json` |
| Browser JavaScript | Syntax check passed | Node.js `--check` |
| Wheel build | Passed | Package contains all 8 fixture/runbook/web asset files |
| Installed package smoke test | Passed | Wheel extracted to a separate temporary directory; CLI returned the expected duplicate-IP report |
| Browser walkthrough | Passed | Duplicate-IP report, retrieved source display, and insufficient-evidence abstention |
| Live model evaluation | 5 / 8 accepted | `qwen3:4b-instruct-2507-q4_K_M`; 8 synthetic cases, bounded validation retries; see `docs/EVALUATION.md` |
| Docker image build | Not run | Docker CLI unavailable in this session |
| Kubernetes deployment | Not run | Manifest provided for a separate reviewed lab deployment |
| GitHub Actions | Not run | Workflow prepared; project has not been published |

The protocol integration test uses a local HTTP stub that follows the Ollama tool-calling message format. It does not prove compatibility with every model, inference quality, or prompt-injection resistance.

The included screenshot shows the reference demo. Its zero model-token usage and deterministic nature are intentional and visible. The live-model result is kept separate from the deterministic baseline.
