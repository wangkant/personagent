# personagent installer for Windows. Nothing needs to be installed first:
#
#   irm https://raw.githubusercontent.com/wangkant/personagent/main/install.ps1 | iex
#
# It fetches uv (which brings its own Python), installs personagent with it,
# puts an icon on the desktop and opens the app. Run it again to update.
#
# Settings, as environment variables:
#   PERSONAGENT_VERSION      install this version instead of the newest
#   PERSONAGENT_MIRROR       auto (default), cn (always use the mirrors), off (never)
#   PERSONAGENT_NO_START     1: do not open the app at the end
#   PERSONAGENT_NO_SHORTCUT  1: no desktop or Start menu icon
#   PERSONAGENT_UV_DIR       where uv goes when it is not installed yet
#   PERSONAGENT_NO_MODIFY_PATH  1: leave PATH as it is
#
# ASCII only: Windows PowerShell 5.1 reads a script without a BOM in the
# system code page, so the Chinese sentences are written as \u escapes.

$PersonagentIndexMirrors = @(
    'https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple',
    'https://mirrors.aliyun.com/pypi/simple'
)
$PersonagentPythonMirror = 'https://registry.npmmirror.com/-/binary/python-build-standalone'
$PersonagentPython = '3.12'
$PersonagentMinUv = New-Object Version 0, 8, 0

function Write-PaLine {
    # One sentence in the system's language: English, or Chinese given as \u escapes.
    param([string]$En, [string]$Zh = '', [string]$Color = '')
    $text = $En
    if ($Zh -and [Globalization.CultureInfo]::CurrentUICulture.Name -like 'zh*') {
        $text = [regex]::Unescape($Zh)
    }
    if ($Color) { Write-Host $text -ForegroundColor $Color } else { Write-Host $text }
}

function Test-PaUrl {
    param([string]$Url, [int]$Seconds = 8)
    try {
        $null = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing -TimeoutSec $Seconds
        return $true
    } catch {
        return $false
    }
}

function Get-PaWheelTag {
    # $null on a processor uv has no Windows build for.
    $arch = $env:PROCESSOR_ARCHITEW6432
    if (-not $arch) { $arch = $env:PROCESSOR_ARCHITECTURE }
    switch ($arch) {
        'AMD64' { return 'win_amd64' }
        'ARM64' { return 'win_arm64' }
        default { return $null }
    }
}

function Find-PaUvWheel {
    # The newest uv wheel a PEP 503 index lists for this processor: its URL and SHA-256.
    param([string]$Index, [string]$Tag)
    $base = $Index.TrimEnd('/') + '/uv/'
    $page = (Invoke-WebRequest -Uri $base -UseBasicParsing -TimeoutSec 30).Content
    $pattern = 'href="([^"#]*?uv-(\d+)\.(\d+)\.(\d+)-py3-none-' + [regex]::Escape($Tag) + '\.whl)(?:#sha256=([0-9a-fA-F]{64}))?"'
    $best = $null
    foreach ($m in [regex]::Matches($page, $pattern)) {
        $version = New-Object Version ([int]$m.Groups[2].Value), ([int]$m.Groups[3].Value), ([int]$m.Groups[4].Value)
        if (-not $best -or $version -gt $best.Version) {
            $best = @{
                Version = $version
                Url     = (New-Object Uri ((New-Object Uri $base), $m.Groups[1].Value)).AbsoluteUri
                Sha256  = $m.Groups[5].Value
            }
        }
    }
    if (-not $best) { throw "no uv wheel for $Tag at $base" }
    return $best
}

function Install-PaUv {
    # Download uv from a package index into $Dir; the path of uv.exe.
    param([string]$Dir, [string[]]$Indexes)
    $tag = Get-PaWheelTag
    if (-not $tag) { throw 'unsupported processor' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $last = $null
    foreach ($index in $Indexes) {
        $wheel = Join-Path ([IO.Path]::GetTempPath()) ("personagent-uv-" + [Guid]::NewGuid().ToString('N') + ".zip")
        try {
            $found = Find-PaUvWheel -Index $index -Tag $tag
            Invoke-WebRequest -Uri $found.Url -OutFile $wheel -UseBasicParsing -TimeoutSec 600
            if ($found.Sha256) {
                $actual = (Get-FileHash -LiteralPath $wheel -Algorithm SHA256).Hash
                if ($actual -ne $found.Sha256.ToUpperInvariant()) { throw "checksum mismatch for $($found.Url)" }
            }
            $null = New-Item -ItemType Directory -Force -Path $Dir
            $zip = [IO.Compression.ZipFile]::OpenRead($wheel)
            try {
                $copied = 0
                foreach ($entry in $zip.Entries) {
                    if ($entry.FullName -match '\.data/scripts/(uvx?w?\.exe)$') {
                        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, (Join-Path $Dir $Matches[1]), $true)
                        $copied++
                    }
                }
            } finally {
                $zip.Dispose()
            }
            $uv = Join-Path $Dir 'uv.exe'
            if (-not $copied -or -not (Test-Path -LiteralPath $uv)) { throw "no uv.exe inside $($found.Url)" }
            return $uv
        } catch {
            $last = $_
        } finally {
            Remove-Item -LiteralPath $wheel -Force -ErrorAction SilentlyContinue
        }
    }
    throw $last
}

function Test-PaUvRecent {
    param([string]$Exe)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try { $said = "$(& $Exe --version 2>$null)" } catch { $said = '' }
    $ErrorActionPreference = $previous
    if ($said -match 'uv (\d+)\.(\d+)\.(\d+)') {
        return ((New-Object Version ([int]$Matches[1]), ([int]$Matches[2]), ([int]$Matches[3])) -ge $PersonagentMinUv)
    }
    return $false
}

function Test-PaForeignCopy {
    # A personagent in uv's executable folder that uv did not put there (pip --user, pipx).
    param([string]$Uv)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $bin = "$(& $Uv tool dir --bin 2>$null)".Trim()
        $listed = "$(& $Uv tool list 2>$null)"
    } catch { $bin = ''; $listed = '' }
    $ErrorActionPreference = $previous
    if (-not $bin) { return $false }
    return ((Test-Path -LiteralPath (Join-Path $bin 'personagent.exe')) -and ($listed -notmatch '(?m)^personagent '))
}

function Get-PaUv {
    # uv already on this computer, else a fresh copy; the path of the executable.
    param([string[]]$Indexes)
    $found = Get-Command uv -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    # An older uv lacks `uv tool` or `--default-index`; it would fail and read as a network fault.
    if ($found -and (Test-PaUvRecent $found.Source)) { return $found.Source }
    $dir = $env:PERSONAGENT_UV_DIR
    if (-not $dir) { $dir = Join-Path $env:USERPROFILE '.local\bin' }
    $kept = Join-Path $dir 'uv.exe'
    if (Test-Path -LiteralPath $kept) { return $kept }
    Write-PaLine 'Fetching uv, which installs Python and personagent...' '\u6b63\u5728\u83b7\u53d6 uv\uff08\u7528\u4e8e\u5b89\u88c5 Python \u548c personagent\uff09...'
    return Install-PaUv -Dir $dir -Indexes $Indexes
}

function Invoke-PaNative {
    # A native command whose stderr is progress, not an error; its exit code.
    param([string]$Exe, [string[]]$Arguments)
    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $Exe @Arguments | Out-Host
        return $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previous
    }
}

function Install-Personagent {
    $ErrorActionPreference = 'Stop'
    $ProgressPreference = 'SilentlyContinue'
    # Windows PowerShell 5.1 on older systems still offers TLS 1.0 first.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    Write-Host ''
    Write-Host '  personagent' -ForegroundColor Cyan
    Write-Host ''
    if (-not (Get-PaWheelTag)) {
        Write-PaLine 'personagent needs 64-bit Windows (x64 or ARM64).' 'personagent \u9700\u8981 64 \u4f4d Windows\uff08x64 \u6216 ARM64\uff09\u3002' Red
        return $false
    }

    $mode = "$env:PERSONAGENT_MIRROR".Trim().ToLowerInvariant()
    if ($mode -notin @('cn', 'off')) { $mode = 'auto' }
    $indexMirror = $false
    $pythonMirror = $false
    if ($mode -eq 'cn') {
        $indexMirror = $true
        $pythonMirror = $true
    } elseif ($mode -eq 'auto') {
        Write-PaLine 'Checking the network...' '\u6b63\u5728\u68c0\u67e5\u7f51\u7edc...'
        $indexMirror = -not (Test-PaUrl 'https://pypi.org/simple/personagent/')
        # A release asset, as the Python download is one.
        $pythonMirror = -not (Test-PaUrl 'https://github.com/astral-sh/python-build-standalone/releases/download/20241016/SHA256SUMS')
        if ($indexMirror -or $pythonMirror) {
            Write-PaLine 'PyPI or GitHub is slow to reach from here; using mirrors in mainland China.' 'PyPI \u6216 GitHub \u8bbf\u95ee\u4e0d\u7545\uff0c\u5c06\u6539\u7528\u4e2d\u56fd\u5927\u9646\u7684\u955c\u50cf\u3002'
        }
    }
    $indexes = @('https://pypi.org/simple') + $PersonagentIndexMirrors
    if ($indexMirror) { $indexes = $PersonagentIndexMirrors + @('https://pypi.org/simple') }

    try {
        $uv = Get-PaUv -Indexes $indexes
    } catch {
        Write-PaLine "uv could not be downloaded: $($_.Exception.Message)" '' Red
        Write-PaLine 'Check the network connection and proxy settings, then run this again.' '\u8bf7\u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u548c\u4ee3\u7406\u8bbe\u7f6e\uff0c\u7136\u540e\u91cd\u65b0\u8fd0\u884c\u3002' Red
        return $false
    }

    $spec = 'personagent'
    if ($env:PERSONAGENT_VERSION) { $spec = "personagent==$($env:PERSONAGENT_VERSION)" }
    if ($env:PERSONAGENT_PACKAGE) { $spec = $env:PERSONAGENT_PACKAGE }

    Write-PaLine 'Installing personagent. The first time this downloads Python and takes a few minutes...' '\u6b63\u5728\u5b89\u88c5 personagent\u3002\u9996\u6b21\u5b89\u88c5\u9700\u4e0b\u8f7d Python\uff0c\u7ea6\u9700\u51e0\u5206\u949f...'
    $force = Test-PaForeignCopy $uv
    if ($force) {
        Write-PaLine 'Replacing the personagent that was installed another way (pip or pipx).' '\u6b63\u5728\u66ff\u6362\u4ee5\u5176\u4ed6\u65b9\u5f0f\uff08pip \u6216 pipx\uff09\u5b89\u88c5\u7684 personagent\u3002'
    }
    $attempts = @(@{ Index = $indexMirror; Python = $pythonMirror })
    if ($mode -eq 'auto' -and -not ($indexMirror -and $pythonMirror)) {
        $attempts += @{ Index = $true; Python = $true }
    }
    $code = 1
    $savedPythonMirror = $env:UV_PYTHON_INSTALL_MIRROR
    try {
        foreach ($attempt in $attempts) {
            $arguments = @('tool', 'install', '--python', $PersonagentPython, '--upgrade')
            if ($force) { $arguments += '--force' }
            # On the command line, so that later upgrades of the tool use it too.
            if ($attempt.Index -and -not $env:UV_DEFAULT_INDEX) { $arguments += @('--default-index', $PersonagentIndexMirrors[0]) }
            if ($attempt.Python -and -not $savedPythonMirror) { $env:UV_PYTHON_INSTALL_MIRROR = $PersonagentPythonMirror }
            $arguments += $spec
            $code = Invoke-PaNative $uv $arguments
            if ($code -eq 0) { break }
            if ($attempt -ne $attempts[-1]) {
                Write-PaLine 'That did not work; trying again through mirrors in mainland China...' '\u5b89\u88c5\u672a\u6210\u529f\uff0c\u6539\u7528\u4e2d\u56fd\u5927\u9646\u7684\u955c\u50cf\u91cd\u8bd5...' Yellow
            }
        }
    } finally {
        $env:UV_PYTHON_INSTALL_MIRROR = $savedPythonMirror
    }
    if ($code -ne 0) {
        Write-PaLine 'personagent could not be installed. If it is open, quit it first; otherwise check the network connection and proxy settings. Then run this again.' 'personagent \u672a\u80fd\u5b89\u88c5\u3002\u5982\u679c personagent \u6b63\u5728\u8fd0\u884c\uff0c\u8bf7\u5148\u9000\u51fa\uff1b\u5426\u5219\u8bf7\u68c0\u67e5\u7f51\u7edc\u8fde\u63a5\u548c\u4ee3\u7406\u8bbe\u7f6e\u3002\u7136\u540e\u91cd\u65b0\u8fd0\u884c\u3002' Red
        return $false
    }

    $previous = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $bin = "$(& $uv tool dir --bin 2>$null)".Trim()
    $tools = "$(& $uv tool dir 2>$null)".Trim()
    # So that `personagent` and `uv` work in terminals opened from now on.
    if (-not $env:PERSONAGENT_NO_MODIFY_PATH) { & $uv tool update-shell *> $null }
    $ErrorActionPreference = $previous
    $exe = Join-Path $bin 'personagent.exe'
    if (-not (Test-Path -LiteralPath $exe)) {
        Write-PaLine "personagent was installed, but $exe is missing." '' Red
        return $false
    }
    if (($env:Path -split ';') -notcontains $bin) { $env:Path = "$bin;$env:Path" }

    if (-not $env:PERSONAGENT_NO_SHORTCUT) {
        $null = Invoke-PaNative $exe @('shortcut')
    }

    Write-Host ''
    Write-PaLine 'personagent is installed.' 'personagent \u5df2\u5b89\u88c5\u3002' Green
    Write-PaLine '  Open it:    the personagent icon on the desktop, or `personagent` in a new terminal' '  \u6253\u5f00\uff1a\u53cc\u51fb\u684c\u9762\u4e0a\u7684 personagent \u56fe\u6807\uff0c\u6216\u5728\u65b0\u7ec8\u7aef\u4e2d\u8fd0\u884c personagent'
    Write-PaLine '  Update it:  the App view of the page, or run this installer again' '  \u66f4\u65b0\uff1a\u5728\u9875\u9762\u7684\u300c\u5e94\u7528\u300d\u89c6\u56fe\u4e2d\u66f4\u65b0\uff0c\u6216\u91cd\u65b0\u8fd0\u884c\u6b64\u5b89\u88c5\u547d\u4ee4'
    Write-PaLine '  Remove it:  uv tool uninstall personagent' '  \u5378\u8f7d\uff1auv tool uninstall personagent'
    Write-Host ''

    if (-not $env:PERSONAGENT_NO_START) {
        Write-PaLine 'Opening personagent...' '\u6b63\u5728\u6253\u5f00 personagent...'
        # pythonw: the window needs no console behind it.
        $quiet = Join-Path $tools 'personagent\Scripts\pythonw.exe'
        if (Test-Path -LiteralPath $quiet) {
            Start-Process -FilePath $quiet -ArgumentList '-m', 'persona_agent', 'start'
        } else {
            Start-Process -FilePath $exe -ArgumentList 'start'
        }
    }
    return $true
}

# start.ps1 loads the functions above without running the installer.
if (-not $PersonagentInstallLib) {
    $PersonagentInstalled = Install-Personagent
    # Under `irm | iex` an exit would close the person's own window.
    if ($MyInvocation.MyCommand.Path -and -not $PersonagentInstalled) { exit 1 }
}
