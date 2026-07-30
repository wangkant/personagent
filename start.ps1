# persona-llm-agent — one-click start (Windows)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$port = if ($env:PORT) { $env:PORT } else { 8080 }
$bindHost = if ($env:HOST) { $env:HOST } else { '127.0.0.1' }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   persona-llm-agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Prefer the venv that quickstart.py creates; fall back to a global interpreter.
$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $pySource = $venvPy
} else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "error: python / python3 not found. Run 'python quickstart.py' first." -ForegroundColor Red
        exit 1
    }
    $pySource = $py.Source
}

# Dependency check
& $pySource -c "import fastapi, uvicorn, dotenv, httpx, PIL, ddgs" 2>$null
if (-not $?) {
    Write-Host "installing dependencies..." -ForegroundColor Yellow
    & $pySource -m pip install -r requirements.txt -q
}

# Avoid mojibake for non-ASCII console output on Windows
$env:PYTHONIOENCODING = 'utf-8'

Write-Host ""
Write-Host "listen:   http://${bindHost}:$port" -ForegroundColor Cyan
Write-Host "webhook:  http://${bindHost}:$port/webhook/qq" -ForegroundColor Cyan
Write-Host ""

& $pySource -m uvicorn main:app --host $bindHost --port $port
