pyinstaller dmm-tools.spec --noconfirm

for /f "delims=" %%i in ('python ../version.py') do set "Ver=%%i"

cd dist
7za a -sfx7z.sfx dmm-tools-%Ver%.exe dmm-tools
