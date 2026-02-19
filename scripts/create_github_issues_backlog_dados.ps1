param(
    [string]$Repo = "",
    [string]$IssuesPath = "docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md",
    [switch]$Apply,
    [switch]$SkipLabelSync
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-GhPath {
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    $fallbacks = @(
        "C:\Program Files\GitHub CLI\gh.exe",
        "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe"
    )
    foreach ($path in $fallbacks) {
        if (Test-Path $path) {
            return $path
        }
    }
    throw "gh CLI not found in PATH or default install locations."
}

function Invoke-Gh {
    param(
        [Parameter(Mandatory = $true)][string]$GhPath,
        [Parameter(Mandatory = $true)][string[]]$Args
    )
    $output = & $GhPath @Args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "gh command failed: gh $($Args -join ' ')`n$output"
    }
    return $output
}

function Get-LabelColor {
    param([Parameter(Mandatory = $true)][string]$Label)
    if ($Label.StartsWith("area:")) { return "1F6FEB" }
    if ($Label.StartsWith("type:feature")) { return "0E8A16" }
    if ($Label.StartsWith("type:infra")) { return "5319E7" }
    if ($Label.StartsWith("type:quality")) { return "C2E0C6" }
    if ($Label.StartsWith("type:docs")) { return "0075CA" }
    if ($Label.StartsWith("priority:p0")) { return "B60205" }
    if ($Label.StartsWith("priority:p1")) { return "D93F0B" }
    if ($Label.StartsWith("priority:p2")) { return "FBCA04" }
    if ($Label.StartsWith("sprint:")) { return "C5DEF5" }
    return "BFDADC"
}

if (-not (Test-Path $IssuesPath)) {
    throw "Issues file not found: $IssuesPath"
}

$content = Get-Content $IssuesPath -Raw -Encoding UTF8
$regex = [regex]::new("(?ms)^###\s+(BD-\d{3}\s+-\s+.+?)\r?\n(.*?)(?=^###\s+BD-\d{3}\s+-|\z)")
$matches = $regex.Matches($content)

if ($matches.Count -eq 0) {
    throw "No issue sections found in $IssuesPath."
}

$issues = @()
foreach ($match in $matches) {
    $title = $match.Groups[1].Value.Trim()
    $section = $match.Groups[2].Value.Trim()
    $labels = @()
    $dependencies = "nenhuma"
    $descriptionLines = @()
    $acceptanceLines = @()
    $inDescription = $false
    $inAcceptance = $false

    foreach ($line in ($section -split "`r?`n")) {
        $trimmed = $line.Trim()
        if ($trimmed -like "- Labels:*") {
            $raw = $trimmed.Substring(9).Trim()
            $labels = $raw.Split(",") | ForEach-Object { ($_.Trim() -replace '[`"]', "") } | Where-Object { $_ }
            continue
        }
        if ($trimmed -like "- Dependencias:*") {
            $dependencies = $trimmed.Substring(15).Trim()
            continue
        }
        if ($trimmed -eq "- Descricao:") {
            $inDescription = $true
            $inAcceptance = $false
            continue
        }
        if ($trimmed -eq "- Checklist de aceite:") {
            $inDescription = $false
            $inAcceptance = $true
            continue
        }
        if ($inDescription -and $trimmed.StartsWith("-")) {
            $descriptionLines += $trimmed.Substring(1).Trim()
            continue
        }
        if ($inAcceptance -and $trimmed.StartsWith("- [ ]")) {
            $acceptanceLines += $trimmed
            continue
        }
    }

    $bodyParts = @()
    if ($descriptionLines.Count -gt 0) {
        $bodyParts += "## Contexto"
        foreach ($item in $descriptionLines) {
            $bodyParts += "- $item"
        }
    }
    $bodyParts += ""
    $bodyParts += "## Dependencias"
    $bodyParts += "- $dependencies"
    $bodyParts += ""
    if ($acceptanceLines.Count -gt 0) {
        $bodyParts += "## Checklist de Aceite"
        $bodyParts += $acceptanceLines
        $bodyParts += ""
    }
    $bodyParts += "## Referencia"
    $bodyParts += "- docs/BACKLOG_DADOS_NIVEL_MAXIMO.md"
    $bodyParts += "- docs/GITHUB_ISSUES_BACKLOG_DADOS_NIVEL_MAXIMO.md"
    $body = ($bodyParts -join "`n")

    $issues += [pscustomobject]@{
        Title = $title
        Labels = $labels
        Body = $body
    }
}

Write-Host "Found $($issues.Count) issue(s) in package."
Write-Host "Mode: $(if ($Apply.IsPresent) { 'APPLY' } else { 'DRY-RUN' })"

if (-not $Apply) {
    foreach ($issue in $issues) {
        $labelDisplay = if ($issue.Labels.Count -gt 0) { $issue.Labels -join ", " } else { "(sem labels)" }
        Write-Host ""
        Write-Host "Issue: $($issue.Title)"
        Write-Host "Labels: $labelDisplay"
    }
    Write-Host ""
    Write-Host "Dry-run finished. Use -Apply to create/update issues."
    Write-Host "Example:"
    Write-Host "  powershell -ExecutionPolicy Bypass -File scripts/create_github_issues_backlog_dados.ps1 -Repo vthamada/territorial-intelligence-platform -Apply"
    exit 0
}

$gh = Get-GhPath
Invoke-Gh -GhPath $gh -Args @("--version") | Out-Null

$repoArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Repo)) {
    $repoArgs = @("--repo", $Repo)
}

if (-not $SkipLabelSync) {
    $existingLabelsJson = Invoke-Gh -GhPath $gh -Args (@("label", "list", "--limit", "500", "--json", "name") + $repoArgs)
    $existingLabels = @{}
    foreach ($item in ($existingLabelsJson | ConvertFrom-Json)) {
        $existingLabels[$item.name] = $true
    }
    $wantedLabels = $issues | ForEach-Object { $_.Labels } | Select-Object -Unique
    foreach ($label in $wantedLabels) {
        if ($existingLabels.ContainsKey($label)) {
            continue
        }
        $color = Get-LabelColor -Label $label
        Invoke-Gh -GhPath $gh -Args (@("label", "create", $label, "--color", $color, "--description", $label) + $repoArgs) | Out-Null
        Write-Host "Created missing label: $label"
    }
}

$existingIssuesJson = Invoke-Gh -GhPath $gh -Args (@("issue", "list", "--state", "all", "--limit", "500", "--json", "number,title") + $repoArgs)
$existingByTitle = @{}
foreach ($item in ($existingIssuesJson | ConvertFrom-Json)) {
    $existingByTitle[$item.title] = [int]$item.number
}

foreach ($issue in $issues) {
    Write-Host ""
    Write-Host "Issue: $($issue.Title)"
    Write-Host "Labels: $($issue.Labels -join ', ')"

    $tmpBody = [System.IO.Path]::GetTempFileName()
    try {
        Set-Content -Path $tmpBody -Value $issue.Body -Encoding UTF8

        if ($existingByTitle.ContainsKey($issue.Title)) {
            $number = $existingByTitle[$issue.Title]
            $editArgs = @("issue", "edit", "$number", "--body-file", $tmpBody) + $repoArgs
            foreach ($label in $issue.Labels) {
                $editArgs += @("--add-label", $label)
            }
            Invoke-Gh -GhPath $gh -Args $editArgs | Out-Null
            Write-Host "Updated existing issue #$number."
        } else {
            $createArgs = @("issue", "create", "--title", $issue.Title, "--body-file", $tmpBody) + $repoArgs
            foreach ($label in $issue.Labels) {
                $createArgs += @("--label", $label)
            }
            $createdOutput = Invoke-Gh -GhPath $gh -Args $createArgs
            Write-Host "Created. $createdOutput"
        }
    } finally {
        if (Test-Path $tmpBody) {
            Remove-Item -Path $tmpBody -Force
        }
    }
}
