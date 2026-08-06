@echo off

::
:: Remove .dat files association
::

:: Check for administrative permissions
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Requesting administrative privileges...
    powershell -Command "Start-Process -Verb RunAs -FilePath '%0'
    exit /b
)

assoc .dat=
ftype DMMData=

reg delete "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.dat" /f
