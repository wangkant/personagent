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
if ([Console]::IsInputRedirected -and -not (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.env')) -and -not $env:LLM_API_KEY) {
    Write-Host "error: setup is needed. Double-click start.bat to open the setup page." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $venvPy)) {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $py) {
        Write-Host "error: python / python3 not found. Install Python 3.10 or newer, then start this again." -ForegroundColor Red
        exit 1
    }
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv')) {
        Write-Error "Incomplete .venv. Move it aside, then start this again."
        exit 1
    }
    & $py.Source -m venv (Join-Path $PSScriptRoot '.venv')
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$pySource = $venvPy

# Install again when the dependency list changed, so a pull that brings a new
# dependency installs it; a version bump alone needs no network.
$project = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'pyproject.toml') -Raw
$deps = [regex]::Match($project, '(?ms)^dependencies = \[.*?^\]').Value
$sha = [System.Security.Cryptography.SHA256]::Create()
$wanted = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($deps))) -replace '-', ''
$stamp = Join-Path $PSScriptRoot '.venv/.personagent-installed'
$installed = if (Test-Path -LiteralPath $stamp) { "$(Get-Content -LiteralPath $stamp -Raw)".Trim() } else { '' }
if ($installed -ne $wanted) {
    Write-Host "installing dependencies..." -ForegroundColor Yellow
    # PS 5.1 trap: under Stop, a native command writing to stderr is a
    # terminating error, so suspend Stop and read $LASTEXITCODE.
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    # Best effort: the pip of Python 3.10.0-3.10.2 cannot install a project editable.
    & $pySource -m pip install -q --upgrade "pip>=21.3" > $null 2>&1
    & $pySource -m pip install -e $PSScriptRoot -q
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prevEAP
    if ($code -eq 0) {
        Set-Content -LiteralPath $stamp -Value $wanted -Encoding ascii
    } elseif ($installed) {
        Write-Host "warning: could not update the dependencies (check the network or proxy); starting with the installed ones." -ForegroundColor Yellow
    } else {
        Write-Host "error: installing the dependencies failed. Check the network connection and proxy settings, then start this again." -ForegroundColor Red
        exit $code
    }
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
