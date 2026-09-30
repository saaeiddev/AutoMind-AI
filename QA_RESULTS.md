# AutoMind AI 0.1.0 - QA Results

## Completed in the current build environment

Build environment used for these checks: Linux x86_64, Python 3.13, headless X11 for UI smoke testing.

- Python compile check: PASS
- Automated test suite: **34 passed**
- `main.py --self-test`: PASS
- Simulation Mode: PASS for all 10 scenarios at logic level
- DTC parsing: PASS for spaced and compact ELM327 responses
- PID decoding: PASS for representative RPM, coolant, voltage and supported-PID responses
- Deterministic diagnostic rules: PASS for lean, misfire and low-voltage scenarios
- SQLite persistence: PASS
- Vehicle profile persistence: PASS
- VIN profile reuse lookup: PASS
- Generated-report registry persistence: PASS
- AI privacy sanitizer / structured response parser: PASS
- Session notes excluded from cloud AI by default: PASS
- PDF report generation: PASS
- PDF visual render verification: PASS, 2 pages, no clipping/overlap observed
- Desktop UI headless smoke test: PASS across all 10 navigation pages
- Session notes + generated report history smoke flow: PASS
- Dashboard visual capture: PASS at 1280x800
- Application icon assets: generated in PNG and ICO formats

## Windows production QA that is prepared but NOT executed here

The current execution environment is Linux and does not contain a Windows runtime, Wine, PyInstaller Windows bootloader build environment, or Inno Setup compiler. Therefore the following claims are intentionally **not** marked as tested in this environment:

- Native `AutoMindAI.exe` produced on Windows
- `AutoMindAI-Setup.exe` compiled with Inno Setup
- Windows 11 launch test
- Windows 11 high-DPI rendering test
- Silent install / installed self-test / uninstall test
- Physical ELM327 + real vehicle hardware test
- Cloud AI online test against a production AutoMind backend (no backend credentials/endpoint were supplied)

The repository includes a Windows CI workflow and `scripts/build_windows.ps1` that perform the missing EXE/installer build and install/uninstall QA on a real Windows runner. The workflow uploads both `AutoMindAI.exe` and `AutoMindAI-Setup.exe` only after the packaged self-test and installed self-test pass.

## Hardware caveat

ELM327 support is implemented against standard serial behavior, but adapter clones and vehicle ECUs vary. Real-hardware certification requires testing with representative adapters/vehicles and should be completed before commercial release.
