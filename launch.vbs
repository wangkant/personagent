' Optional one-click launcher for Windows.
'
' What it does:
'   1. Starts NapCat (your OneBot v11 client) in a minimized cmd window
'   2. Waits a few seconds for NapCat to come up
'   3. Starts main.py in another minimized cmd window
'
' Both windows stay open after launch (cmd /k) so you can see logs / errors.
' Both are minimized without stealing focus (intWindowStyle = 7).
'
' SETUP:
'   1. Edit the three values below (BOT_QQ, NAPCAT_DIR, AGENT_DIR) to match
'      your local install.
'   2. Double-click this .vbs (or pin a shortcut to it on the desktop).
'
' Notes:
'   - File is pure ASCII on purpose; .vbs with non-ASCII characters needs a
'     UTF-8 BOM or cscript will silently fail to start it on some locales.
'   - NapCat's launcher-user.bat takes the bot's QQ number as its first arg.
'     If you use a different OneBot client, adjust the NapCat line accordingly.

Option Explicit

' ---- EDIT THESE ----
Const BOT_QQ      = "0000000000"
Const NAPCAT_DIR  = "E:\NapCat\NapCat.Shell"
Const AGENT_DIR   = "C:\path\to\qq-persona-agent"
' --------------------

Dim WS
Set WS = CreateObject("WScript.Shell")

' Launch NapCat (7 = minimized, no focus)
WS.Run "cmd /k ""cd /d " & NAPCAT_DIR & " && launcher-user.bat " & BOT_QQ & """", 7, False

' Give NapCat ~3s to come up before the agent starts hitting its HTTP API
WScript.Sleep 3000

' Launch the agent
WS.Run "cmd /k ""cd /d " & AGENT_DIR & " && set PYTHONIOENCODING=utf-8 && python main.py""", 7, False
