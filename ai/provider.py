from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class AIProviderError(RuntimeError):
    pass


class AIProvider(ABC):
    name = "abstract"

    @abstractmethod
    def analyze(self, payload: dict[str, Any], question: str = "") -> dict[str, Any]: ...


@dataclass
class BackendAIProvider(AIProvider):
    endpoint: str
    token_env: str = "AUTOMIND_CLIENT_TOKEN"
    timeout_seconds: int = 30
    name: str = "AutoMind Backend"

    def analyze(self, payload: dict[str, Any], question: str = "") -> dict[str, Any]:
        if not self.endpoint:
            raise AIProviderError("AutoMind backend URL is not configured.")
        token = os.getenv(self.token_env, "")
        body = json.dumps({"diagnostic_context": payload, "question": question}).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = urllib.request.Request(self.endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
                data = json.loads(raw)
        except urllib.error.HTTPError as exc:
            safe_body = exc.read().decode("utf-8", errors="replace")[:300]
            raise AIProviderError(f"AI backend returned HTTP {exc.code}: {safe_body}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise AIProviderError(f"AI backend unavailable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise AIProviderError("AI backend returned invalid JSON.") from exc
        if not isinstance(data, dict):
            raise AIProviderError("AI backend response must be a JSON object.")
        return data
