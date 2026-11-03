"""Provider boundary. Demo is deliberately deterministic; Ollama performs real inference."""
import json
import urllib.error
import urllib.parse
import urllib.request


def tool_call(name, **arguments):
    return {"role": "assistant", "content": "", "tool_calls": [
        {"function": {"name": name, "arguments": arguments}}]}


class DemoProvider:
    name = "demo"
    model = "deterministic-reference-policy"
    usage = {"input_tokens": 0, "output_tokens": 0}

    def respond(self, messages, tools):
        observations = {}
        chunks = []
        called = set()
        for message in messages:
            if message.get("role") != "tool":
                continue
            called.add(message["tool_name"])
            value = json.loads(message["content"])
            if "id" in value:
                observations[value["id"]] = value["data"]
            chunks.extend(value.get("chunks", []))
        for name in ["inspect_node", "read_events"]:
            if name not in called:
                return tool_call(name)
        events = " ".join(observations.get("evidence:events", [])).lower()
        # A transparent reference policy, not an LLM and not a ground-truth oracle.
        preferred = "inspect_network" if "reset" in events else (
            "inspect_storage" if "replica" in events else "inspect_workload")
        for name in [preferred, "inspect_network", "inspect_storage", "inspect_workload"]:
            if name not in called:
                return tool_call(name)
        diagnosis = "insufficient_evidence"
        network = observations.get("evidence:network", {})
        storage = observations.get("evidence:storage", {})
        workload = observations.get("evidence:workload", {})
        if len(set(network.get("arp_responders", []))) > 1:
            diagnosis = "duplicate_ip"
        elif storage.get("schedulable") is False and storage.get("provisioned_gib", 0) > storage.get("scheduling_limit_gib", 0):
            diagnosis = "storage_capacity"
        elif workload.get("last_termination") == "OOMKilled":
            diagnosis = "container_oom"
        queries = {
            "duplicate_ip": "duplicate IP ARP MAC control-plane connection reset safe response",
            "storage_capacity": "replica scheduling provisioned capacity limit storage safe response",
            "container_oom": "OOMKilled container memory limit restarting safe response",
            "insufficient_evidence": "insufficient evidence latency safe escalation request traces"
        }
        if not chunks:
            return tool_call("search_runbooks", query=queries[diagnosis], limit=3)
        summaries = {
            "duplicate_ip": "Two distinct MAC addresses claim the affected IP. This supports an address conflict and explains why a successful ping can coexist with intermittent control-plane connections.",
            "storage_capacity": "Provisioned replica capacity exceeds the scheduling limit even though physical disk usage is low. The evidence supports a replica scheduling capacity problem.",
            "container_oom": "The application was OOMKilled and its memory peak reached its container limit. This supports container-level memory pressure, not a demonstrated VM memory shortage.",
            "insufficient_evidence": "The collected observations do not establish a root cause for latency. Request traces and dependency timings before recommending a change."
        }
        steps = {
            "duplicate_ip": ["Verify the owners of both observed MAC addresses in authoritative inventory.", "After owner approval, isolate the unintended interface and correct its persistent IP allocation.", "Verify etcd health, ARP ownership, and node readiness over time."],
            "storage_capacity": ["Verify backing-store capacity and the dedicated disk identity.", "Plan a disk and filesystem expansion; keep the scheduling safety policy intact.", "Verify replica health and run a fresh backup after recovery."],
            "container_oom": ["Profile application memory and investigate leaks or load changes.", "Propose a justified container limit adjustment within node capacity.", "Validate readiness and restart counts under representative load."],
            "insufficient_evidence": ["Collect request traces and dependency timings.", "Correlate latency with deployments and representative load.", "Keep multiple hypotheses open until new evidence is available."]
        }
        return {"role": "assistant", "content": json.dumps({
            "diagnosis": diagnosis, "summary": summaries[diagnosis],
            "evidence_ids": list(observations), "citations": [c["id"] for c in chunks],
            "next_steps": steps[diagnosis],
            "limitations": "Synthetic observations only. The reference policy is not model inference; proposed actions have not been executed."
        })}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Model endpoint redirects are disabled")


class OllamaProvider:
    name = "ollama"

    def __init__(self, model, base_url="http://127.0.0.1:11434", timeout=35):
        parsed = urllib.parse.urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or parsed.path not in {"", "/"}):
            raise ValueError("Ollama must use a loopback HTTP endpoint without credentials or a path")
        if not isinstance(model, str) or not model.strip() or len(model) > 160:
            raise ValueError("An explicit Ollama model is required")
        self.model = model
        self.url = base_url.rstrip("/") + "/api/chat"
        self.timeout = timeout
        self.settings = {"temperature": 0, "seed": 0, "num_predict": 1200, "num_ctx": 8192}
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        # Ignore HTTP proxy environment variables; synthetic evidence stays local.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def respond(self, messages, tools):
        request = urllib.request.Request(self.url, data=json.dumps({
            "model": self.model, "messages": messages, "tools": tools,
            "stream": False, "think": False, "options": self.settings
        }).encode(), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(512_001)
            if len(raw) > 512_000:
                raise ValueError("Model response exceeded size limit")
            body = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Local Ollama returned HTTP {exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            reason = getattr(exc, "reason", None) or str(exc)
            raise RuntimeError(f"Local Ollama request failed: {reason}") from exc
        for source, destination in [("prompt_eval_count", "input_tokens"), ("eval_count", "output_tokens")]:
            count = body.get(source, 0)
            if type(count) is not int or count < 0:
                raise ValueError("Invalid provider token usage")
            self.usage[destination] += count
        message = body.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise ValueError("Invalid model response message")
        # Preserve tool-call metadata but do not store or expose model reasoning.
        return {key: message[key] for key in ["role", "content", "tool_calls"] if key in message}


class OpenAICompatibleProvider:
    """Optional OpenAI-compatible provider (for example OpenRouter).

    Disabled unless explicitly configured through environment variables. The
    provider receives the same bounded tools and prompts as the local model.
    """

    name = "openai-compatible"

    def __init__(self, model, base_url, api_key, timeout=35):
        self.model, self.base_url, self.api_key, self.timeout = model, base_url.rstrip("/"), api_key, timeout
        self.usage = {"input_tokens": 0, "output_tokens": 0}

    def respond(self, messages, tools):
        request = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps({"model": self.model, "messages": messages, "tools": tools, "temperature": 0, "stream": False}).encode(),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.load(response)
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("OpenAI-compatible provider is unavailable") from exc
        choices = body.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0].get("message"), dict):
            raise ValueError("Invalid OpenAI-compatible response")
        usage = body.get("usage", {})
        self.usage["input_tokens"] += usage.get("prompt_tokens", 0) if type(usage.get("prompt_tokens", 0)) is int else 0
        self.usage["output_tokens"] += usage.get("completion_tokens", 0) if type(usage.get("completion_tokens", 0)) is int else 0
        message = choices[0]["message"]
        if message.get("role") != "assistant":
            raise ValueError("Invalid model response message")
        return {key: message[key] for key in ["role", "content", "tool_calls"] if key in message}
