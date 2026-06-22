$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root "venv\Scripts\python.exe"
$frontend = Join-Path $root "frontend"
$pidFile = Join-Path $root ".edu-assistant.pids.json"

& $python -m pip install -r (Join-Path $root "requirements.txt")
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (!(Test-Path (Join-Path $frontend "node_modules"))) {
    npm install --prefix $frontend
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
npm run build --prefix $frontend
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$api = Start-Process -FilePath $python -ArgumentList "-m","uvicorn","src.api.app:app","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -WindowStyle Hidden -PassThru
@{ api = $api.Id } | ConvertTo-Json | Set-Content $pidFile
Write-Host "Edu Assistant iniciado em http://localhost:8000"
