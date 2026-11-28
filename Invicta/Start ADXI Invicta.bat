@echo off
title ADXI: Invicta
rem Starts ADXI: Invicta from the folder this file is in (the one holding atlas.py).
cd /d "%~dp0"
set PY=python
where python >nul 2>nul || set PY=py
rem First run only: install Shapely, the geometry library the scan uses.
%PY% -c "import shapely" >nul 2>nul || (echo Installing Shapely, the geometry library the app uses. This happens once. & %PY% -m pip install --user -r requirements.txt)
echo Starting ADXI: Invicta. Your browser will open in a moment.
echo Keep this window open while you use the app. Close it to stop the app.
echo.
%PY% atlas.py
if errorlevel 1 pause
