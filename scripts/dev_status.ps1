$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stateFile = Join-Path $repoRoot ".dev-processes.json"

if (-not (Test-Path $stateFile)) {
    Write-Host "Arquivo de estado nao encontrado: $stateFile"
    Write-Host "Nenhum ambiente local registrado neste workspace."
    exit 0
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json

function Get-ProcessStatus([int]$Pid) {
    if ($Pid -le 0) {
        return "nao informado"
    }

    $proc = Get-Process -Id $Pid -ErrorAction SilentlyContinue
    if ($null -eq $proc) {
        return "inativo"
    }

    return "ativo"
}

$apiPid = [int]($state.api_pid | ForEach-Object { $_ })
$frontendPid = [int]($state.frontend_pid | ForEach-Object { $_ })

Write-Host "Workspace oficial: $repoRoot"
Write-Host "Arquivo de estado: $stateFile"
Write-Host ""
Write-Host ("API: PID {0} ({1}) -> {2}" -f $apiPid, (Get-ProcessStatus $apiPid), $state.api_url)
Write-Host ("Frontend: PID {0} ({1}) -> {2}" -f $frontendPid, (Get-ProcessStatus $frontendPid), $state.frontend_url)
