# Security and Privacy

## Vehicle safety

AutoMind AI V1 is deliberately read-focused.

Not implemented:

- ECU flashing
- firmware updates
- immobilizer bypass
- odometer changes
- arbitrary CAN writes
- safety-system disabling
- steering/braking/ABS/airbag modification
- hidden DTC clearing

## AI secrets

Production provider secrets belong on the AutoMind backend. The desktop accepts only an optional client token through an environment variable and never writes that token into SQLite or the settings JSON.

## Diagnostic payload sanitation

Before cloud upload:

- personal-data keys such as owner/contact/address/location fields are removed,
- VIN is removed unless explicitly permitted,
- session notes are omitted unless explicitly permitted,
- vehicle profile notes, local image paths and internal record IDs are not placed in AI context,
- only structured diagnostic context is sent.

## Local data

SQLite, settings and logs are written under the current Windows user profile, not Program Files. Reports are written under Documents.

## Logging

Logs are intended to include application state, hardware detection, OBD errors, AI request failures and report-generation errors. Provider secrets must never be logged.

## Backend hardening for commercial deployment

The included backend is a reference implementation. A production deployment should add:

- TLS termination
- user/device authentication
- rate limiting
- request size limits
- structured secret storage
- audit logging
- abuse detection
- key rotation
- strict CORS/network policy as appropriate
- provider timeout/retry policy
- deployment monitoring
