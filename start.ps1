# personagent - open local setup and chat from a checkout (Windows)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot


Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   personagent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# The checkout's own venv; a global interpreter is only used to create it.
$venvRelative = if ([System.Environment]::OSVersion.Platform -eq 'Win32NT') {
    '.venv/Scripts/python.exe'
} else {
    '.venv/bin/python'
}
$venvPy = Join-Path $PSScriptRoot $venvRelative
$basePy = $null
if ([Console]::IsInputRedirected -and -not (Test-Path (Join-Path $PSScriptRoot '.env')) -and -not $env:LLM_API_KEY) {
    Write-Host "error: setup is needed. Double-click start.bat to open the setup page." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $venvPy)) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "error: python / python3 not found. Install Python 3.10 or newer, then start this again." -ForegroundColor Red
        exit 1
    }
    if (Test-Path (Join-Path $PSScriptRoot '.venv')) {
        Write-Error "Incomplete .venv. Move it aside, then start this again."
        exit 1
    }
    $basePy = $py.Source
}

if (-not (Test-Path $venvPy)) {
    & $basePy -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    if (-not (Test-Path $venvPy)) {
        throw "Virtual environment creation did not produce $venvRelative"
    }
}
$pySource = $venvPy

# Install again whenever pyproject.toml changed, so a pull that brings a new
# dependency installs it. PS 5.1 trap: under Stop, a native command writing to
# stderr is a terminating error, so suspend Stop and read $LASTEXITCODE.
$stamp = Join-Path $PSScriptRoot '.venv/.personagent-installed'
$wanted = (Get-FileHash -LiteralPath (Join-Path $PSScriptRoot 'pyproject.toml') -Algorithm SHA256).Hash
$installed = if (Test-Path $stamp) { (Get-Content -LiteralPath $stamp -Raw).Trim() } else { '' }
if ($installed -ne $wanted) {
    Write-Host "installing dependencies..." -ForegroundColor Yellow
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $pySource -m pip install -e $PSScriptRoot -q
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -ne 0) { exit $code }
    Set-Content -LiteralPath $stamp -Value $wanted -Encoding ascii
}

# Avoid mojibake for non-ASCII console output on Windows
$env:PYTHONIOENCODING = 'utf-8'

Write-Host ""
if (-not [Console]::IsInputRedirected -and $args.Count -eq 0) {
    & $pySource -m persona_agent start
} else {
    & $pySource -m persona_agent run @args
}
exit $LASTEXITCODE
