@echo off
rem Ukonci bezici prepinac oken - ciste (WM_CLOSE hlavnimu oknu), po 5 s bez odezvy natvrdo.
rem Logika je ve stop_switcher.ps1 (ukoncuje JEN procesy python s win_switcher.pyw).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_switcher.ps1"
timeout /t 2 >nul
