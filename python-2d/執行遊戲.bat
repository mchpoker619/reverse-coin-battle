@echo off
cd /d "%~dp0"
set PY=python
where py >nul 2>&1 && set PY=py
echo Installing pygame-ce ...
%PY% -m pip install --upgrade pygame-ce
if errorlevel 1 (
  echo.
  echo [ERROR] pygame-ce install failed. Please take a screenshot of this window.
  pause
  exit /b
)
echo.
echo Starting game ...
%PY% reverse_coin.py
pause
