param(
    [switch]$SkipTests,
    [switch]$SkipInstallTest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== AutoMind AI Windows Production Build ==" -ForegroundColor Cyan

if (-not (Get-Command py -ErrorAction SilentlyContinue) -and -not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python 3.12+ is required to build AutoMind AI."
}
$Python = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }

if (-not (Test-Path ".venv")) {
    if ($Python -eq "py") { & py -3.12 -m venv .venv } else { & python -m venv .venv }
}
$Py = Join-Path $Root ".venv\Scripts\python.exe"
& $Py -m pip install --upgrade pip
& $Py -m pip install -r requirements-dev.txt

if (-not $SkipTests) {
    & $Py -m pytest -q
}

Remove-Item -Recurse -Force build -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
& $Py -m PyInstaller AutoMindAI.spec --clean --noconfirm

$Exe = Join-Path $Root "dist\AutoMindAI.exe"
if (-not (Test-Path $Exe)) { throw "PyInstaller did not produce AutoMindAI.exe" }
Write-Host "Running packaged executable self-test..." -ForegroundColor Yellow
& $Exe --self-test
if ($LASTEXITCODE -ne 0) { throw "Packaged AutoMindAI.exe self-test failed" }

$InnoCandidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$ISCC = $InnoCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $ISCC) {
    throw "Inno Setup 6 was not found. Install it, or run the GitHub Actions Windows workflow which installs it automatically."
}

& $ISCC "installer\AutoMindAI.iss"
$Installer = Join-Path $Root "dist\installer\AutoMindAI-Setup.exe"
if (-not (Test-Path $Installer)) { throw "Inno Setup did not produce AutoMindAI-Setup.exe" }

if (-not $SkipInstallTest) {
    Write-Host "Testing silent install / launch / uninstall..." -ForegroundColor Yellow
    $TestDir = Join-Path $env:TEMP "AutoMindAI-InstallTest"
    Remove-Item -Recurse -Force $TestDir -ErrorAction SilentlyContinue
    & $Installer /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- "/DIR=$TestDir"
    $InstalledExe = Join-Path $TestDir "AutoMindAI.exe"
    if (-not (Test-Path $InstalledExe)) { throw "Installer test failed: application EXE missing after install" }
    & $InstalledExe --self-test
    if ($LASTEXITCODE -ne 0) { throw "Installed application self-test failed" }
    $Uninstaller = Join-Path $TestDir "unins000.exe"
    if (-not (Test-Path $Uninstaller)) { throw "Installer test failed: uninstaller missing" }
    & $Uninstaller /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
    Start-Sleep -Seconds 2
    if (Test-Path $InstalledExe) { throw "Uninstall test failed: application executable still exists" }
}

$HashLines = @(
    (Get-FileHash $Exe -Algorithm SHA256 | ForEach-Object { "{0}  AutoMindAI.exe" -f $_.Hash.ToLowerInvariant() }),
    (Get-FileHash $Installer -Algorithm SHA256 | ForEach-Object { "{0}  AutoMindAI-Setup.exe" -f $_.Hash.ToLowerInvariant() })
)
$HashLines | Set-Content -Encoding ascii (Join-Path $Root "dist\SHA256SUMS.txt")

Write-Host "Build complete:" -ForegroundColor Green
Write-Host "  $Exe"
Write-Host "  $Installer"
Write-Host "  $(Join-Path $Root 'dist\SHA256SUMS.txt')"
