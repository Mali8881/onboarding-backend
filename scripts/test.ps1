$ErrorActionPreference = "Stop"

$python = if (Test-Path ".\venv\Scripts\python.exe") {
    ".\venv\Scripts\python.exe"
} else {
    "python"
}

Write-Host "[quality-gate] Ruff (critical rules)"
& $python -m ruff check . --select E9,F63,F7,F82
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[quality-gate] Django check"
& $python manage.py check
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "[quality-gate] Pytest"
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
