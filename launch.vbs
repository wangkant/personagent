' personagent - open the same welcome page as start.bat.
Option Explicit
Dim shell, files, folder
Set shell = CreateObject("WScript.Shell")
Set files = CreateObject("Scripting.FileSystemObject")
folder = files.GetParentFolderName(WScript.ScriptFullName)
shell.Run """" & folder & "\start.bat" & """", 1, False
