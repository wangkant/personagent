# onebot-llm-agent — one-click start (Windows)
$port = if ($env:PORT) { $env:PORT } else { 8080 }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   onebot-llm-agent" -ForegroundColor Cyan
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
& $pySource -c "import fastapi, uvicorn, dotenv, httpx, anthropic" 2>$null
if (-not $?) {
    Write-Host "installing dependencies..." -ForegroundColor Yellow
    & $pySource -m pip install -r requirements.txt -q
}

# Avoid mojibake for non-ASCII console output on Windows
$env:PYTHONIOENCODING = 'utf-8'

$hostIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress
if (-not $hostIp) { $hostIp = '<your-ip>' }

Write-Host ""
Write-Host "local:    http://127.0.0.1:$port" -ForegroundColor Cyan
Write-Host "LAN:      http://${hostIp}:$port" -ForegroundColor Cyan
Write-Host "webhook:  http://${hostIp}:$port/webhook/qq" -ForegroundColor Cyan
Write-Host ""

& $pySource -m uvicorn main:app --host 0.0.0.0 --port $port
