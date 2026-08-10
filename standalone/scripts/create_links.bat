@echo off

::
:: Creates links to binaries on Windows desktop
::

cd /d "%~dp0"

pushd ..
if not exist data mkdir data
popd

call .mk_link.bat ut61xp-Start ut61xp-start.exe
call .mk_link.bat ut61xp-plot  ut61xp-plot.exe
call .mk_link.bat ut61xp-hist  ut61xp-hist.exe
call .mk_link.bat ut61xp-stat  ut61xp-stat.exe
call .mk_link.bat ut61xp-data  data

::
:: Preload on startup helps to improve next app start time
::
call .mk_link.bat ut61xp-preload ut61xp-start.exe "--preload --quit" "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
