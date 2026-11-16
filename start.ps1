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

# The oldest Python the dependencies install on (requires-python in pyproject.toml).
$minPython = [version]'3.10'

function Get-PythonVersion {
    # $null when it does not run: the Microsoft Store alias named python.exe is not Python.
    param([string]$Exe, [string[]]$Pre = @())
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $said = $null
    try {
        $said = & $Exe @Pre -c "import sys; print('.'.join(map(str, sys.version_info[:3])))" 2>$null
        if ($LASTEXITCODE -ne 0) { $said = $null }
    } catch {
        $said = $null
    }
    $ErrorActionPreference = $prevEAP
    $line = @($said) | Where-Object { "$_" -match '^\d+\.\d+\.\d+$' } | Select-Object -Last 1
    if ($line) { return [version]"$line" }
    return $null
}

if (-not (Test-Path -LiteralPath $venvPy)) {
    # python.org's installer leaves Python off PATH by default, but installs the py launcher.
    $candidates = @(
        @{ Name = 'python'; Pre = @() },
        @{ Name = 'python3'; Pre = @() },
        @{ Name = 'py'; Pre = @('-3') }
    )
    $py = $null
    $tooOld = $null
    foreach ($candidate in $candidates) {
        $found = Get-Command $candidate.Name -CommandType Application -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if (-not $found) { continue }
        $version = Get-PythonVersion $found.Source $candidate.Pre
        if (-not $version) { continue }
        if ($version -ge $minPython) {
            $py = @{ Source = $found.Source; Pre = $candidate.Pre }
            break
        }
        if (-not $tooOld) { $tooOld = "Python $version ($($found.Source))" }
    }
    # install.ps1 beside this file can fetch a Python; a copy without it cannot.
    $installer = Join-Path $PSScriptRoot 'install.ps1'
    $canFetch = Test-Path -LiteralPath $installer
    if (-not $py -and -not $canFetch -and $tooOld) {
        Write-Host "error: found $tooOld, but personagent needs Python $minPython or newer. Install a newer Python, then start this again." -ForegroundColor Red
        exit 1
    }
    if (-not $py -and -not $canFetch) {
        Write-Host "error: python / python3 / py not found. Install Python $minPython or newer, then start this again." -ForegroundColor Red
        exit 1
    }
    if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv')) {
        Write-Error "Incomplete .venv. Move it aside, then start this again."
        exit 1
    }
    if ($py) {
        $pre = $py.Pre
        & $py.Source @pre -m venv (Join-Path $PSScriptRoot '.venv')
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    } else {
        # No usable Python here: uv brings one, as install.ps1 does.
        if ($tooOld) { Write-Host "found $tooOld, which is older than Python $minPython." -ForegroundColor Yellow }
        Write-Host "fetching Python (once, a few minutes)..." -ForegroundColor Yellow
        $PersonagentInstallLib = $true
        . $installer
        $ProgressPreference = 'SilentlyContinue'
        [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
        $fetchHelp = "Check the network connection and proxy settings, or install Python $minPython or newer yourself, then start this again."
        try {
            $uv = Get-PaUv -Indexes (@('https://pypi.org/simple') + $PersonagentIndexMirrors)
        } catch {
            Write-Host "error: Python could not be fetched ($($_.Exception.Message)). $fetchHelp" -ForegroundColor Red
            exit 1
        }
        # --seed: the steps below install with the environment's own pip.
        $venvArgs = @('venv', '--python', $PersonagentPython, '--seed', (Join-Path $PSScriptRoot '.venv'))
        $code = Invoke-PaNative $uv $venvArgs
        if ($code -ne 0 -and -not $env:UV_PYTHON_INSTALL_MIRROR) {
            # GitHub is slow or closed from mainland China; the mirrors carry the same files.
            Remove-Item -LiteralPath (Join-Path $PSScriptRoot '.venv') -Recurse -Force -ErrorAction SilentlyContinue
            $env:UV_PYTHON_INSTALL_MIRROR = $PersonagentPythonMirror
            if (-not $env:PIP_INDEX_URL) { $env:PIP_INDEX_URL = $PersonagentIndexMirrors[0] }
            $code = Invoke-PaNative $uv $venvArgs
        }
        if ($code -ne 0) {
            Write-Host "error: Python could not be fetched. $fetchHelp" -ForegroundColor Red
            exit $code
        }
    }
} else {
    # A .venv whose Python was uninstalled, or made with an older one, would fail
    # in pip and read as a network problem.
    $venvVersion = Get-PythonVersion $venvPy
    if (-not $venvVersion) {
        Write-Host "error: .venv here no longer runs; most often the Python it was made with is gone (uninstalled or moved). Delete the .venv folder, then start this again to rebuild it." -ForegroundColor Red
        exit 1
    }
    if ($venvVersion -lt $minPython) {
        Write-Host "error: .venv here was made with Python $venvVersion, but personagent needs Python $minPython or newer. Install a newer Python, move .venv aside, then start this again." -ForegroundColor Red
        exit 1
    }
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
    $quietPy = Join-Path (Split-Path -Parent $pySource) 'pythonw.exe'
    if (Test-Path -LiteralPath $quietPy) {
        # Once per checkout: a deleted icon stays deleted.
        $iconStamp = Join-Path $PSScriptRoot '.venv/.personagent-shortcut'
        if (-not (Test-Path -LiteralPath $iconStamp)) {
            & $pySource -m persona_agent shortcut
            if ($LASTEXITCODE -eq 0) { Set-Content -LiteralPath $iconStamp -Value 'made' -Encoding ascii }
        }
        # The window needs no console behind it, so this one can close.
        Start-Process -FilePath $quietPy -ArgumentList '-m', 'persona_agent', 'start' -WorkingDirectory $PSScriptRoot
        exit 0
    }
    & $pySource -m persona_agent start
} else {
    & $pySource -m persona_agent run @args
}
exit $LASTEXITCODE
