# Windows Production Build

## Outputs

The production pipeline is designed to create:

- `dist\AutoMindAI.exe`
- `dist\installer\AutoMindAI-Setup.exe`
- `dist\SHA256SUMS.txt`

## Required build machine

- Windows 11 x64 or GitHub `windows-latest`
- Python 3.12
- Internet access for Python build dependencies
- Inno Setup 6

End users do **not** need Python, pip, Node.js, Visual Studio or a terminal.

## One-command build

```powershell
.\scripts\build_windows.ps1
```

## Build validation

The script performs:

1. Python unit/integration tests.
2. PyInstaller build.
3. `AutoMindAI.exe --self-test`.
4. Inno Setup compilation.
5. Silent installer test into a temporary folder.
6. Installed executable self-test.
7. Silent uninstall.
8. Verification that the installed executable was removed.
9. SHA-256 generation for the application executable and installer.

The self-test exercises Simulation Mode, DTC analysis, live PID generation, SQLite persistence and PDF generation.

## GitHub Actions

`.github/workflows/windows-build.yml` runs the same process on Windows and uploads the EXE and installer as an Actions artifact.

## Code signing

The installer and executable are unsigned unless a real code-signing certificate is supplied. Do not claim a digital signature when none exists. Windows SmartScreen may warn about an unknown publisher.

A future signed release workflow should sign **both** the application executable and installer before distribution.
