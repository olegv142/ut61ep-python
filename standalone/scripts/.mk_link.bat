@echo off

pushd ..

set "shortcutPath=%userprofile%\Desktop\%1.lnk"
for %%I in ("%2") do set "targetPath=%%~fI"

powershell -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%shortcutPath%'); $s.TargetPath = '%targetPath%'; $s.Save()"

popd
