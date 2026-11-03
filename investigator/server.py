"""Loopback lab UI and JSON API. Not a public multi-user production server."""
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .agent import investigate
from .connectors import ConnectorConfigurationError, KubernetesReadOnlyConfig, KubernetesReadOnlyConnector
from .providers import DemoProvider, OllamaProvider, OpenAICompatibleProvider
from .tools import scenarios

WEB = Path(__file__).parent / "web"


class Metrics:
    def __init__(self):
        self.lock = threading.Lock()
        self.completed = 0
        self.failed = 0
        self.duration_ms = 0.0
        self.tokens = 0

    def record(self, result=None):
        with self.lock:
            if result is None:
                self.failed += 1
            else:
                self.completed += 1
                self.duration_ms += result["metrics"]["duration_ms"]
                self.tokens += result["metrics"]["input_tokens"] + result["metrics"]["output_tokens"]

    def render(self):
        with self.lock:
            return ("# TYPE investigator_runs_total counter\n"
                    f'investigator_runs_total{{status="completed"}} {self.completed}\n'
                    f'investigator_runs_total{{status="failed"}} {self.failed}\n'
                    "# TYPE investigator_duration_seconds_total counter\n"
                    f"investigator_duration_seconds_total {self.duration_ms / 1000}\n"
                    "# TYPE investigator_model_tokens_total counter\n"
                    f"investigator_model_tokens_total {self.tokens}\n")


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, model=None, ollama_url="http://127.0.0.1:11434"):
        self.model = model
        self.ollama_url = ollama_url
        self.metrics = Metrics()
        self.slots = threading.BoundedSemaphore(2)
        if model:
            OllamaProvider(model, ollama_url)  # Validate config before binding a socket.
        super().__init__(address, Handler)


class Handler(BaseHTTPRequestHandler):
    server_version = "IncidentInvestigator"

    def setup(self):
        super().setup()
        self.connection.settimeout(8)

    def log_message(self, format, *args):
        # No request bodies, event text, or model output in access logs.
        pass

    def send(self, status, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def trusted_host(self):
        host = self.headers.get("Host", "")
        try:
            hostname = urlsplit("http://" + host).hostname
        except ValueError:
            return False
        configured = {item.strip().lower() for item in os.environ.get("INVESTIGATOR_ALLOWED_HOSTS", "").split(",") if item.strip()}
        return hostname in {"localhost", "127.0.0.1", "::1"} | configured

    def do_GET(self):
        path = urlsplit(self.path).path
        # Health probes do not expose application data and work from a container network.
        if path in {"/healthz", "/readyz"}:
            self.send(200, {"status": "ok", "data_mode": "synthetic"})
            return
        if not self.trusted_host():
            self.send(403, {"error": "Untrusted Host header"})
            return
        if path == "/api/scenarios":
            self.send(200, [{k: item[k] for k in ["id", "title", "alert", "resources"]} for item in scenarios()])
        elif path == "/api/live/summary":
            try:
                config = KubernetesReadOnlyConfig.from_environment()
                connector = KubernetesReadOnlyConnector(config)
                self.send(200, {
                    "data_mode": "live-read-only",
                    "api_host": urlsplit(config.api_url).hostname,
                    "observations": {name: len(connector.observe(name)["items"]) for name in ("nodes", "pods", "events")},
                    "mutations_executed": 0,
                })
            except (ConnectorConfigurationError, OSError, RuntimeError, ValueError) as exc:
                self.send(503, {"data_mode": "live-read-only", "available": False, "error": str(exc)})
        elif path == "/api/live/nodes":
            try:
                config = KubernetesReadOnlyConfig.from_environment()
                items = KubernetesReadOnlyConnector(config).observe("nodes")["items"]
                self.send(200, [{
                    "name": item.get("metadata", {}).get("name", "unknown"),
                    "ready": next((condition.get("status") == "True" for condition in item.get("status", {}).get("conditions", []) if condition.get("type") == "Ready"), False),
                    "roles": sorted((item.get("metadata", {}).get("labels", {}).get("node-role.kubernetes.io/worker") and ["worker"] or []) + (["control-plane"] if "node-role.kubernetes.io/control-plane" in item.get("metadata", {}).get("labels", {}) else [])),
                    "kubelet": item.get("status", {}).get("nodeInfo", {}).get("kubeletVersion", "unknown"),
                } for item in items])
            except (ConnectorConfigurationError, OSError, RuntimeError, ValueError) as exc:
                self.send(503, {"available": False, "error": str(exc)})
        elif path == "/api/config":
            self.send(200, {"data_mode": "synthetic", "ollama_enabled": bool(self.server.model),
                            "openrouter_enabled": bool(os.environ.get("INVESTIGATOR_OPENAI_API_KEY")),
                            "model": self.server.model, "version": "0.1.0"})
        elif path == "/metrics":
            self.send(200, self.server.metrics.render(), "text/plain; version=0.0.4")
        else:
            routes = {"/": ("index.html", "text/html; charset=utf-8"),
                      "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                      "/style.css": ("style.css", "text/css; charset=utf-8")}
            if path not in routes:
                self.send(404, {"error": "Not found"})
                return
            filename, mime = routes[path]
            self.send(200, (WEB / filename).read_bytes(), mime)

    def do_POST(self):
        if not self.trusted_host():
            self.send(403, {"error": "Untrusted Host header"})
            return
        origin = self.headers.get("Origin")
        allowed_origins = {"http://" + self.headers.get("Host", ""), "https://" + self.headers.get("Host", "")}
        if origin and origin not in allowed_origins:
            self.send(403, {"error": "Cross-origin requests are not allowed"})
            return
        if urlsplit(self.path).path != "/api/investigate":
            self.send(404, {"error": "Not found"})
            return
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            self.send(415, {"error": "Expected application/json"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4096:
                raise ValueError("Request body must contain 1..4096 bytes")
            body = json.loads(self.rfile.read(size))
            if not isinstance(body, dict) or set(body) - {"scenario_id", "provider", "node_name"}:
                raise ValueError("Unexpected request fields")
            scenario_id = body.get("scenario_id")
            if not isinstance(scenario_id, str) or scenario_id not in {s["id"] for s in scenarios()}:
                raise ValueError("Unknown scenario")
            mode = body.get("provider", "demo")
            if not isinstance(mode, str) or mode not in {"demo", "ollama", "openrouter"}:
                raise ValueError("Unknown provider")
            if mode == "ollama" and not self.server.model:
                raise ValueError("Start the server with --model to enable local inference")
            if mode == "openrouter" and not os.environ.get("INVESTIGATOR_OPENAI_API_KEY"):
                raise ValueError("OpenAI-compatible provider is not configured")
        except (ValueError, UnicodeError) as exc:
            self.send(400, {"error": str(exc)})
            return
        if not self.server.slots.acquire(blocking=False):
            self.send(429, {"error": "Two investigations are already running; try again shortly"})
            return
        try:
            if mode == "demo":
                provider = DemoProvider()
            elif mode == "ollama":
                provider = OllamaProvider(self.server.model, self.server.ollama_url)
            else:
                provider = OpenAICompatibleProvider(os.environ.get("INVESTIGATOR_OPENAI_MODEL", "openai/gpt-4o-mini"), os.environ.get("INVESTIGATOR_OPENAI_BASE_URL", "https://openrouter.ai/api/v1"), os.environ["INVESTIGATOR_OPENAI_API_KEY"])
            result = investigate(scenario_id, provider)
            result["target_node"] = body.get("node_name") or None
            self.server.metrics.record(result)
            self.send(200, result)
        except (ValueError, RuntimeError) as exc:
            self.server.metrics.record()
            self.send(422, {"error": str(exc), "report_generated": False})
        except Exception:
            self.server.metrics.record()
            self.send(500, {"error": "Investigation failed; no diagnosis was accepted", "report_generated": False})
        finally:
            self.server.slots.release()
