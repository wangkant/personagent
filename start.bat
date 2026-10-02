@echo off
setlocal
rem personagent - double-click to start it from this folder (runs start.ps1).
powershell -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
set "PA_EXIT=%ERRORLEVEL%"
rem Keep the window open on a failure so the message can be read.
if not "%PA_EXIT%"=="0" pause
exit /b %PA_EXIT%
