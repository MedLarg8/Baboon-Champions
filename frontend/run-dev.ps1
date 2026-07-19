$ErrorActionPreference = "Stop"

$FrontendRoot = $PSScriptRoot
$NodeModulesPath = Join-Path $FrontendRoot "node_modules"

if (-not (Test-Path -LiteralPath $NodeModulesPath)) {
    Write-Host "Frontend dependencies are not installed." -ForegroundColor Red
    Write-Host "Install them from the frontend directory with:" -ForegroundColor Yellow
    Write-Host "  npm install"
    exit 1
}

Set-Location -LiteralPath $FrontendRoot
npm run dev
