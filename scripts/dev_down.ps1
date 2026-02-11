$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateFile = Join-Path $repoRoot ".dev-processes.json"

if (-not (Test-Path $stateFile)) {
    Write-Host "Arquivo de estado nao encontrado: $stateFile"
    Write-Host "Nada para encerrar."
    exit 0
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json
$pids = @($state.api_pid, $state.frontend_pid) | Where-Object { $_ -ne $null }

foreach ($pid in $pids) {
    $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
    if ($null -ne $proc) {
        Stop-Process -Id $pid -Force
        Write-Host "Processo encerrado: PID $pid"
    } else {
        Write-Host "PID $pid nao estava ativo."
    }
}

Remove-Item -Path $stateFile -Force -ErrorAction SilentlyContinue
Write-Host "Ambiente local encerrado."
