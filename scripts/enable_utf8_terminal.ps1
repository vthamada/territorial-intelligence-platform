Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

[Console]::InputEncoding = $utf8NoBom
[Console]::OutputEncoding = $utf8NoBom
$OutputEncoding = $utf8NoBom
$env:PYTHONUTF8 = "1"

try {
    chcp 65001 > $null
} catch {
    Write-Warning "Nao foi possivel ajustar o code page para 65001 nesta sessao."
}

Write-Host "Terminal configurado para UTF-8."
Write-Host "Console InputEncoding: $([Console]::InputEncoding.WebName)"
Write-Host "Console OutputEncoding: $([Console]::OutputEncoding.WebName)"
Write-Host "PYTHONUTF8=$env:PYTHONUTF8"
