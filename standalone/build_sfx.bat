pyinstaller dmm-tools.spec --noconfirm

for /f "delims=" %%i in ('python ../version.py') do set "Ver=%%i"

7z a -sfx7z.sfx dist/dmm-tools-%Ver%.exe dist/dmm-tools
