@echo off

::
:: Associate .dat files with ut61xp-plot tool
::

:: Check for administrative permissions
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%0'
    exit /b
)

cd /d "%~dp0"
cd ..

for %%I in (ut61xp-plot.exe) do set "targetPath=%%~fI"

reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.dat" /f

assoc .dat=DMMData
ftype DMMData="%targetPath%" "%%1"
