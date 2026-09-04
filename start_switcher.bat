@echo off
cd /d "%~dp0"
rem Ukonci JEN bezici instance prepinace (python proces s win_switcher.pyw v prikazove radce).
rem Drivejsi "taskkill /im pythonw.exe" zabijel VSECHNY pythonw aplikace v systemu.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^python' -and $_.CommandLine -match 'win_switcher\.pyw' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
timeout /t 1 >nul
start pythonw win_switcher.pyw
echo Window Switcher spusten na pozadí!
echo Vyvolani: zkratka podle config.txt (hotkey_modifier / hotkey_key).
timeout /t 3 >nul
