# AutoMind AI

AutoMind AI is a Windows 11 x64 automotive diagnostics desktop application with ELM327/OBD-II support, deterministic diagnostic rules, vehicle/session history, PDF reports, simulation scenarios, and an optional privacy-aware AI backend.

## Highlights
- Real read-focused ELM327 / OBD-II architecture
- Stored, pending and permanent DTC reading
- Live PID data and freeze-frame support
- Vehicle profiles and diagnostic history
- 10 built-in simulation scenarios
- Deterministic diagnostic reasoning with evidence vs. possible causes
- Privacy-aware optional AI provider architecture
- Professional PDF diagnostic reports
- SQLite local data storage
- Windows installer and standalone executable
- Automated tests and Windows CI

## Platform
- Windows 11 x64
- Python 3.12
- Tk / ttk desktop UI
- PySerial
- SQLite
- ReportLab
- FastAPI reference AI backend
- PyInstaller
- Inno Setup

## Installation
Download `AutoMindAI-Setup.exe` from the repository release files, run it, and follow the installer. The installer is currently unsigned, so Windows SmartScreen may display an Unknown Publisher warning.

## Build from source
Install Python 3.12 and Inno Setup, then run:

```powershell
.\scripts\build_windows.ps1
```

The project also includes `BUILD_WINDOWS.bat` and GitHub Actions configuration for reproducible Windows builds.

## Safety
AutoMind AI is intentionally read-focused. It does **not** implement ECU flashing, arbitrary CAN transmission, or DTC clearing.

## Hardware validation
The Windows package has passed automated build, packaged self-test, silent install, installed-app self-test, and uninstall QA on a GitHub Windows runner. Physical ELM327 + real-vehicle testing is still required for hardware-specific validation.

## AI configuration
Production API keys are not embedded in the desktop application. The AI layer is provider-swappable and can connect to the included reference backend. See `docs/AI.md` and `docs/AI_BACKEND_ENV.example`.

## Privacy
VIN and session notes are excluded from AI requests by default. Sensitive owner/location fields are sanitized before optional AI processing.

## Documentation
Detailed architecture, OBD support, AI, security, QA, plugin architecture, and Windows build documentation are included under `docs/`.

## Author
Created by **Amir Saeid Dehghan**.
