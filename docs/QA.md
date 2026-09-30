# Quality Assurance Status

## Verified in the current build environment

- Automated test suite: **34 passed**
- Python syntax / bytecode compilation: PASS
- `main.py --self-test`: PASS
- Simulation Mode controller flow: PASS
- All ten simulation scenarios emit live data: PASS
- DTC parsing / PID parsing / VIN parsing: PASS
- Simulated ELM327 transport integration: PASS
- SQLite vehicle/session/live-snapshot persistence: PASS
- VIN profile reuse lookup and report registry persistence: PASS
- Local deterministic diagnostic rules: PASS
- AI sanitizer / structured parser / session-note privacy defaults: PASS
- Desktop -> configured backend HTTP path using a local test server: PASS
- PDF report generation: PASS
- Sample PDF visual render inspection: PASS (2 pages, no observed clipping/overlap)
- Desktop UI lifecycle under a virtual display: PASS
- Session notes and generated-report list UI smoke flow: PASS
- Dashboard screenshot generated from running UI: PASS
- Live Data screenshot generated from running UI: PASS

## Windows-specific QA that requires a Windows runner

The repository includes an automated Windows build script and GitHub Actions workflow designed to verify:

- PyInstaller produces `AutoMindAI.exe`
- packaged EXE self-test passes
- Inno Setup produces `AutoMindAI-Setup.exe`
- silent installation succeeds
- installed EXE self-test passes
- uninstaller exists
- silent uninstall succeeds
- installed executable is removed

These Windows-only steps cannot truthfully be marked PASS until the workflow runs on a real Windows runner.

## Hardware validation still required

A physical ELM327/vehicle matrix should validate at least:

- reputable USB ELM327 adapter
- common CAN OBD-II vehicle
- ISO/K-line vehicle if supported by adapter
- ignition-off / ECU-timeout behavior
- unplug/reconnect behavior
- unsupported PID handling
- real freeze-frame availability
- pending and permanent DTC availability

No hardware test result is fabricated in this project.
