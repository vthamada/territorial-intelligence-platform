param(
    [string]$ReferencePeriod = "2025",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python da venv nao encontrado em '$pythonExe'. Crie/ative a .venv antes de executar."
}

$forceLiteral = if ($Force.IsPresent) { "True" } else { "False" }

Push-Location $repoRoot
try {
    $env:PYTHONPATH = "src"

    Write-Host "[ops-routine] Executando ibge_geometries_fetch (reference_period=$ReferencePeriod, force=$forceLiteral)..."
    & $pythonExe -c "from pipelines.ibge_geometries import run; import json; print(json.dumps(run(reference_period='$ReferencePeriod', force=$forceLiteral), ensure_ascii=False))"
    if ($LASTEXITCODE -ne 0) {
        throw "ibge_geometries_fetch falhou com exit code $LASTEXITCODE"
    }

    Write-Host "[ops-routine] Executando quality_suite (reference_period=$ReferencePeriod)..."
    & $pythonExe -c "from pipelines.quality_suite import run; import json; print(json.dumps(run(reference_period='$ReferencePeriod'), ensure_ascii=False))"
    if ($LASTEXITCODE -ne 0) {
        throw "quality_suite falhou com exit code $LASTEXITCODE"
    }

    Write-Host "[ops-routine] Rotina concluida com sucesso."
}
finally {
    Pop-Location
}
