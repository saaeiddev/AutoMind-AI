from ai.sanitize import sanitize_diagnostic_payload
from ai.service import AIService, parse_ai_analysis
from vehicle.models import DiagnosticSession, VehicleProfile


def test_sanitizer_removes_vin_by_default():
    payload = {"vehicle": {"vin": "SECRET", "model": "X"}, "owner": "Name"}
    cleaned = sanitize_diagnostic_payload(payload)
    assert "vin" not in cleaned["vehicle"]
    assert "owner" not in cleaned
    assert cleaned["vehicle"]["model"] == "X"


def test_sanitizer_can_keep_vin_explicitly():
    payload = {"vehicle": {"vin": "ABC"}}
    assert sanitize_diagnostic_payload(payload, include_vin=True)["vehicle"]["vin"] == "ABC"


def test_ai_parser_structured_response():
    result = parse_ai_analysis({
        "summary": "Test",
        "observed_evidence": ["P0171"],
        "possible_causes": ["Vacuum leak"],
        "recommended_steps": ["Smoke test"],
        "additional_measurements": ["Fuel pressure"],
        "confidence": "Moderate",
        "warnings": ["Verify"],
    }, provider="Mock")
    assert result.summary == "Test"
    assert result.provider == "Mock"
    assert result.possible_causes == ["Vacuum leak"]


def test_ai_context_excludes_session_notes_by_default():
    service = AIService(provider=None)  # type: ignore[arg-type]
    session = DiagnosticSession(user_notes="Customer email and symptom notes")
    vehicle = VehicleProfile(manufacturer="Demo", model="Car", vin="VIN123", notes="private profile note")
    context = service.build_context(session, vehicle)
    assert "user_notes" not in context["session"]
    assert "notes" not in context["vehicle"]
    assert context["vehicle"]["vin"] == "VIN123"


def test_ai_context_can_include_session_notes_with_explicit_opt_in():
    service = AIService(provider=None)  # type: ignore[arg-type]
    session = DiagnosticSession(user_notes="Rough idle when cold")
    context = service.build_context(session, None, include_user_notes=True)
    assert context["session"]["user_notes"] == "Rough idle when cold"


def test_ai_context_can_include_minimal_historical_faults():
    service = AIService(provider=None)  # type: ignore[arg-type]
    session = DiagnosticSession()
    history = [{"started_at": "2026-01-01T00:00:00+00:00", "health_status": "Check Recommended", "dtcs": [{"code": "P0171", "status": "Stored"}]}]
    context = service.build_context(session, None, historical_faults=history)
    assert context["historical_faults"] == history


def test_backend_provider_http_roundtrip():
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from ai.provider import BackendAIProvider

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            _ = json.loads(self.rfile.read(length).decode("utf-8"))
            body = json.dumps({
                "summary": "Configured backend reached",
                "observed_evidence": ["P0302"],
                "possible_causes": ["Ignition fault"],
                "recommended_steps": ["Inspect ignition components"],
                "additional_measurements": [],
                "confidence": "Test",
                "warnings": [],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            return

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = BackendAIProvider(f"http://127.0.0.1:{server.server_port}/v1/analyze", timeout_seconds=2)
        result = provider.analyze({"dtcs": ["P0302"]}, "What next?")
        assert result["summary"] == "Configured backend reached"
    finally:
        server.shutdown()
        thread.join(timeout=2)
