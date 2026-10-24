@echo off
chcp 65001 >nul
title 没有编号
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install Python 3 and tick "Add to PATH".
  pause
  exit /b 1
)
python "%~dp0notebook.py" %*
echo.
pause

