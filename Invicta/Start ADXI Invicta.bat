@echo off
title ADXI: Invicta
cd /d "C:\Studio\ArcaneDrift\Invicta"
echo Starting ADXI: Invicta. Your browser will open in a moment.
echo Keep this window open while you use the app. Close it to stop the app.
echo.
where python >nul 2>nul && (python atlas.py) || (py atlas.py)
if errorlevel 1 pause
