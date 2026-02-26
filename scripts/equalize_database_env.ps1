param(
    [string]$TseYears = "2024,2022,2020,2018,2016",
    [string]$IndicatorPeriods = "2024,2025",
    [switch]$IncludeWave7,
    [switch]$SkipFullIncremental,
    [switch]$AllowBackfillBlocked,
    [string]$OutputDir = "data/reports"
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$pythonExe = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $pythonExe)) {
    throw "Python da venv nao encontrado em '$pythonExe'. Crie/ative a .venv antes de executar."
}

if (-not (Test-Path (Join-Path $repoRoot $OutputDir))) {
    New-Item -Path (Join-Path $repoRoot $OutputDir) -ItemType Directory -Force | Out-Null
}

$tseReprocessReport = Join-Path $OutputDir "reprocess_tse_2024.current_env.json"
$robustBackfillReport = Join-Path $OutputDir "robustness_backfill_sync_env.current_env.json"
$incrementalFullReport = Join-Path $OutputDir "incremental_full_sources.current_env.json"
$scorecardReport = Join-Path $OutputDir "data_coverage_scorecard.current_env.json"

function Invoke-Step {
    param(
        [string]$StepName,
        [string[]]$Args,
        [switch]$AllowNonZero
    )

    Write-Host ""
    Write-Host "==> $StepName"
    & $pythonExe @Args
    $exitCode = $LASTEXITCODE

    if ($exitCode -ne 0 -and -not $AllowNonZero.IsPresent) {
        throw "$StepName falhou com exit code $exitCode"
    }

    return $exitCode
}

function Test-OnlyBlockedStatuses {
    param([string]$ReportPath)

    if (-not (Test-Path $ReportPath)) {
        return $false
    }

    $content = Get-Content $ReportPath -Raw -Encoding UTF8
    if ([string]::IsNullOrWhiteSpace($content)) {
        return $false
    }

    $json = $content | ConvertFrom-Json
    if (-not $json.executions) {
        return $false
    }

    $nonSuccess = @($json.executions | Where-Object { $_.status -ne "success" })
    if ($nonSuccess.Count -eq 0) {
        return $true
    }

    return (@($nonSuccess | Where-Object { $_.status -ne "blocked" }).Count -eq 0)
}

Push-Location $repoRoot
try {
    $env:PYTHONPATH = "src"

    Invoke-Step -StepName "sync_connector_registry" -Args @("scripts/sync_connector_registry.py")
    Invoke-Step -StepName "sync_schema_contracts" -Args @("scripts/sync_schema_contracts.py")

    Invoke-Step -StepName "reprocess_tse_2024" -Args @(
        "scripts/run_incremental_backfill.py",
        "--jobs", "tse_catalog_discovery,tse_electorate_fetch,tse_results_fetch",
        "--reprocess-jobs", "tse_electorate_fetch,tse_results_fetch",
        "--reprocess-periods", "2024",
        "--periods", "2024",
        "--output-json", $tseReprocessReport
    )

    $backfillArgs = @(
        "scripts/backfill_robust_database.py",
        "--tse-years", $TseYears,
        "--indicator-periods", $IndicatorPeriods,
        "--output-json", $robustBackfillReport
    )
    if ($IncludeWave7.IsPresent) {
        $backfillArgs += "--include-wave7"
    }

    $backfillExit = Invoke-Step -StepName "backfill_robust_database" -Args $backfillArgs -AllowNonZero
    if ($backfillExit -ne 0) {
        if ($AllowBackfillBlocked.IsPresent -and (Test-OnlyBlockedStatuses -ReportPath $robustBackfillReport)) {
            Write-Warning "backfill_robust_database retornou codigo nao-zero, mas apenas status=blocked foram detectados. Continuando por politica AllowBackfillBlocked."
        }
        else {
            throw "backfill_robust_database falhou com exit code $backfillExit"
        }
    }

    if (-not $SkipFullIncremental.IsPresent) {
        $incrementalArgs = @(
            "scripts/run_incremental_backfill.py",
            "--include-partial",
            "--allow-governed-sources",
            "--output-json", $incrementalFullReport
        )
        if ($AllowBackfillBlocked.IsPresent) {
            $incrementalArgs += "--allow-blocked"
        }

        $incrementalExit = Invoke-Step -StepName "run_incremental_backfill_full_sources" -Args $incrementalArgs -AllowNonZero
        if ($incrementalExit -ne 0) {
            throw "run_incremental_backfill_full_sources falhou com exit code $incrementalExit"
        }
    }
    else {
        Write-Host ""
        Write-Host "==> run_incremental_backfill_full_sources"
        Write-Warning "Etapa ignorada por parametro -SkipFullIncremental."
    }

    Invoke-Step -StepName "apply_polling_places_seed" -Args @("scripts/apply_seed.py")

    Invoke-Step -StepName "export_data_coverage_scorecard" -Args @(
        "scripts/export_data_coverage_scorecard.py",
        "--output-json", $scorecardReport
    )

    Invoke-Step -StepName "backend_readiness" -Args @(
        "scripts/backend_readiness.py",
        "--output-json"
    )

    Write-Host ""
    Write-Host "Equalizacao concluida."
    Write-Host "Relatorios:"
    Write-Host " - $tseReprocessReport"
    Write-Host " - $robustBackfillReport"
    Write-Host " - $incrementalFullReport"
    Write-Host " - $scorecardReport"
}
finally {
    Pop-Location
}
