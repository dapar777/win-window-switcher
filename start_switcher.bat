@echo off
cd /d "%~dp0"
start pythonw win_switcher.pyw
echo Window Switcher spusten na pozadí!
echo Stisknete Ctrl+Shift+Space pro vyvolání.
timeout /t 3 >nul
