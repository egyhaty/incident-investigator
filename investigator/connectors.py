"""Optional, read-only live evidence connectors.

The default application never enables these connectors. Live access requires an
explicit API URL, bearer token, and CA bundle supplied outside the repository.
The connector exposes observations only; it has no write, exec, or log-stream
endpoint and never accepts arbitrary paths from the model.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass
from typing import Any


class ConnectorConfigurationError(ValueError):
    """Raised when live evidence has not been explicitly configured."""


@dataclass(frozen=True)
class KubernetesReadOnlyConfig:
    api_url: str
    token: str
    ca_file: str | None = None
    timeout_seconds: float = 8.0

    @classmethod
    def from_environment(cls) -> "KubernetesReadOnlyConfig":
        api_url = os.environ.get("INVESTIGATOR_K8S_API_URL", "").rstrip("/")
        token = os.environ.get("INVESTIGATOR_K8S_TOKEN", "")
        if not api_url or not token:
            raise ConnectorConfigurationError(
                "Live Kubernetes evidence is disabled; configure INVESTIGATOR_K8S_API_URL and INVESTIGATOR_K8S_TOKEN"
            )
        if not api_url.startswith("https://"):
            raise ConnectorConfigurationError("Kubernetes API URL must use HTTPS")
        return cls(api_url, token, os.environ.get("INVESTIGATOR_K8S_CA_FILE"))


class KubernetesReadOnlyConnector:
    """Small allowlisted Kubernetes API adapter for evidence collection."""

    _paths = {
        "nodes": "/api/v1/nodes",
        "pods": "/api/v1/pods",
        "events": "/api/v1/events",
    }

    def __init__(self, config: KubernetesReadOnlyConfig):
        self.config = config

    def observe(self, resource: str) -> dict[str, Any]:
        try:
            path = self._paths[resource]
        except KeyError as exc:
            raise ValueError(f"Unsupported live observation: {resource}") from exc
        request = urllib.request.Request(
            self.config.api_url + path,
            headers={"Authorization": f"Bearer {self.config.token}", "Accept": "application/json"},
            method="GET",
        )
        context = ssl.create_default_context(cafile=self.config.ca_file)
        with urllib.request.urlopen(request, context=context, timeout=self.config.timeout_seconds) as response:
            if response.status != 200:
                raise RuntimeError(f"Kubernetes API returned HTTP {response.status}")
            payload = json.load(response)
        return {"resource": resource, "items": payload.get("items", []), "source": "kubernetes-api"}
