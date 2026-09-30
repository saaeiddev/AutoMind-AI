$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
$Py = ".venv\Scripts\python.exe"
& $Py -m pip install -r requirements.txt
& $Py main.py
