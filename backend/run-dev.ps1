$ErrorActionPreference = "Stop"

$BackendRoot = $PSScriptRoot
$PythonPath = Join-Path $BackendRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $PythonPath)) {
    Write-Host "Backend virtual environment not found." -ForegroundColor Red
    Write-Host "Create it from the backend directory with:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

Set-Location -LiteralPath $BackendRoot
& $PythonPath -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
