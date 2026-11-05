Set objShell = CreateObject("WScript.Shell")
strPath = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\") - 1)
objShell.CurrentDirectory = strPath

' Roda o servidor Python com janela totalmente oculta (funciona com python.exe normal)
objShell.Run "python.exe " & Chr(34) & strPath & "\app.py" & Chr(34), 0, False

' Aguarda o servidor iniciar antes de abrir o navegador
WScript.Sleep 2500

objShell.Run "http://localhost:5000", 1, False