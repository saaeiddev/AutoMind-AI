@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1"
if errorlevel 1 (
  echo.
  echo AutoMind AI build FAILED. Review the error above.
  pause
  exit /b 1
)
echo.
echo AutoMind AI build completed successfully.
echo Outputs are under the dist folder.
pause
