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

assoc .data=
ftype DMMTools.Data=

