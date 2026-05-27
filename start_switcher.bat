@echo off
cd /d "%~dp0"
taskkill /f /im pythonw3.12.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 1 >nul
start pythonw win_switcher.pyw
echo Window Switcher spusten na pozadí!
echo Stisknete Ctrl+Shift+Space pro vyvolání.
timeout /t 3 >nul
