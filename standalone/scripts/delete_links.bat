@echo off

::
:: Remove links to binaries from Windows desktop
::

del "%userprofile%\Desktop\ut61xp-start.lnk"
del "%userprofile%\Desktop\ut61xp-plot.lnk"
del "%userprofile%\Desktop\ut61xp-hist.lnk"
del "%userprofile%\Desktop\ut61xp-stat.lnk"
del "%userprofile%\Desktop\ut61xp-data.lnk"
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\ut61xp-preload.lnk"
