$ErrorActionPreference = "Stop"

$RepoRoot = $PSScriptRoot
$BackendScript = Join-Path $RepoRoot "backend\run-dev.ps1"
$FrontendScript = Join-Path $RepoRoot "frontend\run-dev.ps1"

Write-Host "Starting ARAM Baboon Tracker development servers..."
Write-Host "Frontend: http://localhost:5173"
Write-Host "Backend:  http://127.0.0.1:8001"
Write-Host "API docs: http://127.0.0.1:8001/docs"

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$BackendScript`""
)

Start-Process -FilePath "powershell.exe" -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$FrontendScript`""
)
