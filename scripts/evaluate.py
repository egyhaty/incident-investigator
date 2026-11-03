"""Small labeled evaluation harness. Demo results are regression checks, not AI benchmarks."""
import argparse
import json
import sys
import time
import platform
import hashlib
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from investigator.agent import Budget, investigate
from investigator.providers import DemoProvider, OllamaProvider
from investigator.tools import load_scenario
from evals.counterexamples import cases as counterexamples


class RecordingProvider:
    """Save public model replies, including rejected reports, without reasoning."""
    def __init__(self, provider):
        self.provider = provider
        self.replies = []
        self.messages = []

    def __getattr__(self, name):
        return getattr(self.provider, name)

    def respond(self, messages, tools):
        self.messages = list(messages)
        reply = self.provider.respond(messages, tools)
        self.replies.append(reply)
        return reply


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=["demo", "ollama"], default="demo")
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--counterexamples", action="store_true")
    parser.add_argument("--seconds", type=float, default=180)
    parser.add_argument("--token-budget", type=int, default=64000)
    args = parser.parse_args()
    if args.provider == "ollama" and not args.model:
        parser.error("--model is required for real Ollama inference")
    if args.seconds <= 0 or args.token_budget <= 0:
        parser.error("Evaluation budgets must be positive")
    rows = []
    cases = [(load_scenario(c["scenario_id"]), c) for c in json.loads((ROOT / "evals/cases.json").read_text())]
    if args.counterexamples:
        cases.extend(counterexamples())
    for scenario, case in cases:
        started = time.monotonic()
        provider = RecordingProvider(DemoProvider() if args.provider == "demo" else OllamaProvider(args.model, timeout=args.seconds))
        try:
            result = investigate(case["scenario_id"], provider, scenario=scenario,
                                 budget=Budget(seconds=args.seconds, tokens=args.token_budget))
            checks = {
                "diagnosis": result["report"]["diagnosis"] == case["expected_diagnosis"],
                "relevant_source": case["expected_source"] in {s["source"] for s in result["sources"]},
                "critical_evidence": case["critical_evidence"] in result["report"]["evidence_ids"],
                "no_mutation": result["policy"]["mutations_executed"] == 0
            }
            rows.append({"scenario": case["scenario_id"], "passed": all(checks.values()),
                         "checks": checks, "metrics": result["metrics"], "result": result})
        except (ValueError, RuntimeError) as exc:
            rows.append({"scenario": case["scenario_id"], "passed": False, "error": str(exc)})
        rows[-1].update(elapsed_seconds=round(time.monotonic() - started, 3),
                        usage=dict(provider.usage), replies=provider.replies,
                        messages=provider.messages,
                        expected=case, settings=getattr(provider, "settings", {}),
                        grounding_review="pending manual review; citation validity does not establish sentence truth")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.with_suffix(".partial.json").write_text(json.dumps(rows, indent=2) + "\n")
    output = {"provider": args.provider, "model": args.model,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "environment": {"python": platform.python_version(), "platform": platform.platform()},
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for folder in ["investigator", "evals", "scripts"] for p in sorted((ROOT / folder).rglob("*"))
                                if p.is_file() and "results" not in p.relative_to(ROOT).parts
                                and p.suffix in {".py", ".json", ".md"}},
              "budget": {"seconds": args.seconds, "tokens": args.token_budget, "rounds": 9, "tool_calls": 12},
              "scope": "Synthetic fixture regression; not model quality evidence" if args.provider == "demo" else "Small synthetic evaluation; not a general capability or safety benchmark",
              "passed": sum(row["passed"] for row in rows), "total": len(rows), "cases": rows}
    if args.provider == "ollama":
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        output["runtime_identity"] = {}
        for endpoint in ["version", "tags"]:
            try:
                with opener.open("http://127.0.0.1:11434/api/" + endpoint, timeout=5) as response:
                    output["runtime_identity"][endpoint] = json.load(response)
            except (OSError, ValueError) as exc:
                output["runtime_identity"][endpoint] = {"error": str(exc)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))
    return 0 if output["passed"] == output["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
