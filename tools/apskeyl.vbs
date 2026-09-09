' apskeyl launcher (silent, no console window)
' ASCII only: wscript reads .vbs as ANSI, Cyrillic literals break paths
Dim sh, here
Set sh = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.Run """" & here & "apskeyl.cmd""", 0, False
