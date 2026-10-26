@echo off
chcp 65001 >nul
title 本子 v0.5.1
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3 and tick "Add to PATH".
  pause
  exit /b 1
)
python "%~dp0notebook_v051.py" %*
echo.
pause
