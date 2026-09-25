# personagent — one-click start (Windows)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot


Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   personagent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Reuse quickstart's venv; a global interpreter is only used to create it.
$venvRelative = if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') {
    '.venv/Scripts/python.exe'
} else {
    '.venv/bin/python'
}
$venvPy = Join-Path $PSScriptRoot $venvRelative
if (Test-Path $venvPy) {
    $pySource = $venvPy
} else {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "error: python / python3 not found. Run 'python quickstart.py' first." -ForegroundColor Red
        exit 1
    }
    if (Test-Path (Join-Path $PSScriptRoot '.venv')) {
        Write-Error "Incomplete .venv. Repair it with quickstart.py or move it aside."
        exit 1
    }
    & $py.Source -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not (Test-Path $venvPy)) {
        throw "Virtual environment creation did not produce $venvRelative"
    }
    $pySource = $venvPy
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
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

# Avoid mojibake for non-ASCII console output on Windows
$env:PYTHONIOENCODING = 'utf-8'

Write-Host ""
# main.py loads .env before resolving SERVER_HOST / SERVER_PORT.
& $pySource main.py
exit $LASTEXITCODE
