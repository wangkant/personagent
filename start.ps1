# personagent — one-click start (Windows)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

$port = if ($env:PORT) { $env:PORT } else { 8080 }
$bindHost = if ($env:HOST) { $env:HOST } else { '127.0.0.1' }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   personagent" -ForegroundColor Cyan
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

# Dependency check. PS 5.1 traps: `2>$null` on a native command becomes a
# terminating error under Stop, and `$?` goes false on any stderr output, so
# suspend Stop and read $LASTEXITCODE instead.
$prevEAP = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $pySource -c "import fastapi, uvicorn, dotenv, httpx, PIL, ddgs" > $null 2>&1
$depsOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEAP
if (-not $depsOk) {
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
