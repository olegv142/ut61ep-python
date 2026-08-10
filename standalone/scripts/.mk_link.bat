@echo off

pushd ..

IF "%~4"=="" (
	set "shortcutPath=%userprofile%\Desktop\%1.lnk"
) else (
	set "shortcutPath=%~4\%1.lnk"
)

for %%I in ("%2") do set "targetPath=%%~fI"

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%shortcutPath%'); $s.TargetPath = '%targetPath%'; $s.Arguments = '%~3'; $s.Save()"

popd
