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

$api = Start-Process -FilePath $python -ArgumentList "-m","uvicorn","src.api.dev_app:app","--reload","--host","127.0.0.1","--port","8000" -WorkingDirectory $root -WindowStyle Hidden -PassThru
$web = Start-Process -FilePath "npm.cmd" -ArgumentList "run","dev","--prefix",$frontend,"--","--host","127.0.0.1" -WorkingDirectory $root -WindowStyle Hidden -PassThru
@{ api = $api.Id; web = $web.Id } | ConvertTo-Json | Set-Content $pidFile
Write-Host "Frontend Vite com hot reload: http://localhost:5173"
Write-Host "API FastAPI: http://localhost:8000"
Write-Host "No modo dev, use a porta 5173 para ver mudancas do frontend."
