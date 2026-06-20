Set shell = CreateObject("WScript.Shell")
project = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

shell.Run "cmd.exe /k """ & project & "\server_mototrack.bat""", 1, False
WScript.Sleep 5000
shell.Run "http://127.0.0.1:8000/connexion/", 1, False
