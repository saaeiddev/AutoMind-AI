# AutoMind AI Architecture

## Principles

AutoMind AI uses a layered architecture so UI, vehicle communications, local reasoning, cloud AI, storage, and reporting remain independently replaceable.

```text
Vehicle / Simulator
      |
      v
OBD Transport + ELM327 Client
      |
      v
Protocol Parser / PID Decoder
      |
      v
Normalized Domain Models
      |
      +--------------------+
      |                    |
      v                    v
Local Rule Engine      SQLite History
      |                    |
      v                    |
Structured Context <-------+
      |
      +------ optional ----> Sanitizer -> AutoMind Backend -> AI Provider
      |
      v
Desktop UI / PDF Reports
```

## Layer responsibilities

### `obd/`
Owns serial transport, ELM327 initialization, standard OBD service commands, response normalization, DTC parsing, supported-PID discovery, VIN decoding and PID decoding.

No arbitrary CAN transmit API exists in V1.

### `vehicle/`
Contains transport-independent dataclasses such as `VehicleProfile`, `PIDValue`, `DTCRecord`, `DiagnosticFinding`, `AIAnalysis`, and `DiagnosticSession`.

### `diagnostics/`
Provides deterministic local interpretation. It may rank hypotheses using available data, but never converts a hypothesis into a confirmed repair diagnosis.

### `knowledge/`
Loads maintainable JSON knowledge for DTC descriptions, causes, checks, symptoms and related PIDs.

### `database/`
Persists profiles, sessions, latest session state, live snapshots and generated-report records in SQLite.

### `ai/`
Contains the provider interface, AutoMind backend client, privacy sanitizer and structured-response parser.

### `backend/`
Reference HTTPS service boundary. Production provider API keys live here rather than in the Windows executable.

### `reports/`
Generates local workshop-style PDFs.

### `ui/`
Owns display, user input, live charting, first-run wizard and all interactive screens. Long-running real-vehicle / AI operations are dispatched away from the UI thread.

### `plugins/`
Defines a future permissioned plugin contract. V1 does not dynamically execute third-party plugins.

## Safety boundaries

The V1 controller does not expose ECU flashing, firmware updating, immobilizer operations, odometer operations, arbitrary CAN writes, braking/steering/airbag/ABS modification, or silent code clearing.

## State model

Connection state is explicit and never inferred from a pretty UI state:

- Vehicle Disconnected
- Adapter Disconnected
- Adapter Connected
- Vehicle Connected
- SIMULATION MODE
- ECU Communication Error
- AI Connecting
- AI Online
- AI Offline
- Historical Session

## Extensibility

Future transports should implement the transport/client boundary and emit the same normalized domain models. Future AI providers should implement the provider interface. Manufacturer plugins should remain capability-scoped and read-only unless a future product version explicitly introduces audited write permissions.
