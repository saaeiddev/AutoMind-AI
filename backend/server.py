"""Reference AutoMind cloud-backend entry point.

This backend is intentionally separate from the desktop installer so provider
secrets never need to ship inside AutoMindAI.exe.

Install `requirements-backend.txt`, set environment variables, then run:
    uvicorn backend.server:app --host 0.0.0.0 --port 8080
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

try:
    from fastapi import FastAPI, Header, HTTPException
    from pydantic import BaseModel
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("Backend dependencies are not installed. See requirements-backend.txt") from exc


app = FastAPI(title="AutoMind AI Backend", version="0.1.0")


class AnalyzeRequest(BaseModel):
    diagnostic_context: dict[str, Any]
    question: str = ""


def _authorize(authorization: str | None) -> None:
    expected = os.getenv("AUTOMIND_BACKEND_CLIENT_TOKEN", "")
    if not expected:
        return
    if authorization != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")


def _system_prompt() -> str:
    return (
        "You are AutoMind AI Assistant, an automotive diagnostic reasoning layer. "
        "Always separate observed ECU/sensor evidence from possible causes. Never invent sensor values. "
        "Do not give instructions for ECU flashing, immobilizer/security bypass, odometer modification, "
        "disabling airbags/ABS/steering/braking systems, or arbitrary CAN injection. "
        "Return JSON only with keys: summary, observed_evidence, possible_causes, recommended_steps, "
        "additional_measurements, confidence, warnings."
    )


def _provider_call(context: dict[str, Any], question: str) -> dict[str, Any]:
    base_url = os.getenv("AUTOMIND_AI_BASE_URL", "").rstrip("/")
    api_key = os.getenv("AUTOMIND_AI_API_KEY", "")
    model = os.getenv("AUTOMIND_AI_MODEL", "")
    if not base_url or not api_key or not model:
        raise HTTPException(status_code=503, detail="AI provider is not configured")
    # OpenAI-compatible Chat Completions request. A different provider adapter can replace this function.
    payload = {
        "model": model,
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": _system_prompt()},
            {"role": "user", "content": json.dumps({"context": context, "question": question}, ensure_ascii=False)},
        ],
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Provider HTTP {exc.code}") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="AI provider unavailable") from exc
    try:
        content = raw["choices"][0]["message"]["content"]
        result = json.loads(content)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Provider returned an invalid structured response") from exc
    if not isinstance(result, dict):
        raise HTTPException(status_code=502, detail="Provider response was not an object")
    return result


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/analyze")
def analyze(request: AnalyzeRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    # The desktop already sanitizes context. The backend performs a second defensive check.
    context = request.diagnostic_context
    text = json.dumps(context)
    if len(text) > 250_000:
        raise HTTPException(status_code=413, detail="Diagnostic payload too large")
    return _provider_call(context, request.question)
