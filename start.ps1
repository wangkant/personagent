# QQ Persona Agent — 一键启动
$port = if ($env:PORT) { $env:PORT } else { 8080 }

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   QQ Persona Agent" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python3 -ErrorAction SilentlyContinue }
if (-not $py) {
    Write-Host "错误: 找不到 python 或 python3" -ForegroundColor Red
    exit 1
}

# 依赖检查
& $py.Source -c "import fastapi, uvicorn, dotenv, httpx, anthropic" 2>$null
if (-not $?) {
    Write-Host "正在安装依赖..." -ForegroundColor Yellow
    & $py.Source -m pip install -r requirements.txt -q
}

# 防止 Windows 控制台中文输出乱码
$env:PYTHONIOENCODING = 'utf-8'

$hostIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
    Select-Object -First 1).IPAddress
if (-not $hostIp) { $hostIp = '<your-ip>' }

Write-Host ""
Write-Host "本机访问:  http://127.0.0.1:$port" -ForegroundColor Cyan
Write-Host "局域网:    http://${hostIp}:$port" -ForegroundColor Cyan
Write-Host "Webhook:   http://${hostIp}:$port/webhook/qq" -ForegroundColor Cyan
Write-Host ""

& $py.Source -m uvicorn main:app --host 0.0.0.0 --port $port
