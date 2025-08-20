param(
  [int]$ApiPort = 8000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

# venv
if (-not (Test-Path ".\.venv\Scripts\Activate.ps1")) {
  python -m venv .venv
}
.\.venv\Scripts\Activate.ps1

# ensure deps
python -m pip install -e . | Out-Null

# set UI → API URL
$env:PRINTSSISTANT_API = "http://127.0.0.1:$ApiPort"

# start API & UI in separate windows
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root'; .\.venv\Scripts\Activate.ps1; python -m uvicorn api.main:app --reload --host 127.0.0.1 --port $ApiPort"
Start-Process powershell -ArgumentList "-NoExit","-Command","cd '$root'; .\.venv\Scripts\Activate.ps1; streamlit run ui\app.py"
