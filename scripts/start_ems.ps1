$ErrorActionPreference = 'Stop'
$workspace = Split-Path $PSScriptRoot -Parent
$backend = Join-Path $workspace 'em-situational-system-main/em-situational-system-main/backend'
$pythonExe = Join-Path $workspace '.venv-ems/Scripts/python.exe'
Set-Location -LiteralPath $backend
& $pythonExe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
