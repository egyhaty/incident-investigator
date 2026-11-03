import argparse
import json
import sys
from pathlib import Path

from .agent import investigate
from .providers import DemoProvider, OllamaProvider
from .server import LabServer
from .tools import scenarios


def main():
    parser = argparse.ArgumentParser(description="Evidence-first incident investigation using synthetic data")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve", help="Start the local lab UI")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--model", help="Installed Ollama model with tool-calling support")
    serve.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    run = commands.add_parser("investigate", help="Run a synthetic incident investigation")
    run.add_argument("--scenario", choices=[s["id"] for s in scenarios()], default="duplicate-ip")
    run.add_argument("--provider", choices=["demo", "ollama"], default="demo")
    run.add_argument("--model")
    run.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            server = LabServer((args.host, args.port), args.model, args.ollama_url)
            print(f"Incident Investigator: http://localhost:{server.server_port} (synthetic data only)", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
        else:
            provider = DemoProvider() if args.provider == "demo" else OllamaProvider(args.model)
            result = investigate(args.scenario, provider)
            text = json.dumps(result, indent=2)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(text + "\n", encoding="utf-8")
            print(text)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Investigation could not complete: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
