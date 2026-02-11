param(
    [string]$ApiHost = "0.0.0.0",
    [int]$ApiPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$apiPython = Join-Path $repoRoot ".venv\\Scripts\\python.exe"
$frontendDir = Join-Path $repoRoot "frontend"
$stateFile = Join-Path $repoRoot ".dev-processes.json"

if (-not (Test-Path $apiPython)) {
    throw "Python da venv nao encontrado em '$apiPython'. Crie a .venv antes de executar."
}

if (-not (Test-Path $frontendDir)) {
    throw "Diretorio frontend nao encontrado em '$frontendDir'."
}

$apiArgs = @(
    "-m", "uvicorn", "app.api.main:app",
    "--app-dir", "src",
    "--reload",
    "--host", $ApiHost,
    "--port", "$ApiPort"
)

$frontendArgs = @(
    "run", "dev", "--",
    "--host", "0.0.0.0",
    "--port", "$FrontendPort"
)

$apiProcess = Start-Process -FilePath $apiPython -ArgumentList $apiArgs -WorkingDirectory $repoRoot -PassThru
$frontendProcess = Start-Process -FilePath "npm.cmd" -ArgumentList $frontendArgs -WorkingDirectory $frontendDir -PassThru

$state = [ordered]@{
    api_pid = $apiProcess.Id
    frontend_pid = $frontendProcess.Id
    api_url = "http://localhost:$ApiPort"
    frontend_url = "http://localhost:$FrontendPort"
}

$state | ConvertTo-Json | Set-Content -Path $stateFile -Encoding UTF8

Write-Host "API iniciada (PID $($apiProcess.Id)) em $($state.api_url)"
Write-Host "Frontend iniciado (PID $($frontendProcess.Id)) em $($state.frontend_url)"
Write-Host "Para parar, execute: powershell -ExecutionPolicy Bypass -File scripts/dev_down.ps1"
