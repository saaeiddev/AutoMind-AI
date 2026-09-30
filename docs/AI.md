# AI Architecture

## Design rule

AI is an optional reasoning layer, not the source of vehicle truth.

The desktop first performs local OBD parsing and deterministic rule analysis. Only then can a sanitized context be sent to a configured AutoMind backend.

When the current session is associated with a saved vehicle profile, the desktop may also include a minimal technical summary of recent sessions for that same vehicle (date, health status, connection mode and DTC code/status only). It does not include historical free-text notes in that history summary.

## Desktop provider contract

`AIProvider.analyze(payload, question) -> structured JSON`

The desktop currently includes `BackendAIProvider`, which posts to a configured backend endpoint.

## Expected structured response

```json
{
  "summary": "...",
  "observed_evidence": ["..."],
  "possible_causes": ["..."],
  "recommended_steps": ["..."],
  "additional_measurements": ["..."],
  "confidence": "...",
  "warnings": ["..."]
}
```

## Privacy

Before upload, the desktop builds an allow-listed vehicle/session context and then applies a second sanitizer pass. Vehicle profile notes, image paths, internal IDs and creation metadata are not part of the cloud context. VIN is removed unless the user explicitly enables VIN transmission. Diagnostic-session notes are excluded by default and are only included when the user separately enables that privacy option.

## Production backend

The reference FastAPI backend reads provider configuration from environment variables:

- `AUTOMIND_AI_BASE_URL`
- `AUTOMIND_AI_API_KEY`
- `AUTOMIND_AI_MODEL`
- optional `AUTOMIND_BACKEND_CLIENT_TOKEN`

The master provider key is never required inside the Windows executable.

Example local backend start:

```powershell
python -m pip install -r requirements-backend.txt
$env:AUTOMIND_AI_API_KEY="..."
$env:AUTOMIND_AI_MODEL="your-model"
uvicorn backend.server:app --host 127.0.0.1 --port 8080
```

Desktop backend endpoint example:

`http://127.0.0.1:8080/v1/analyze`

## Provider abstraction

The reference backend uses an OpenAI-compatible Chat Completions shape internally, but that function is isolated and can be replaced by another cloud provider, a private hosted model, or a local model gateway without changing the desktop diagnostic engine.
