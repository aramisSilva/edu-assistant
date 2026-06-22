$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root ".edu-assistant.pids.json"

function Stop-ProcessTree([int] $ProcessId) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-ProcessTree $_.ProcessId }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

if (Test-Path $pidFile) {
    $pids = Get-Content $pidFile -Raw | ConvertFrom-Json
    @($pids.api, $pids.web) | Where-Object { $_ } | ForEach-Object {
        Stop-ProcessTree $_
    }
    Remove-Item $pidFile
}

Get-NetTCPConnection -LocalPort 8000,5173 -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { Stop-ProcessTree $_ }

Write-Host "Processos do Edu Assistant encerrados."
