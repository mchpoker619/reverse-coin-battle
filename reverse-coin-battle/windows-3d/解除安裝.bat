@echo off
cd /d "%TEMP%"
if not exist "%LOCALAPPDATA%\ReverseCoin3D\game\uninstall.ps1" (
  echo Reverse Coin 3D is not installed.
  pause
  exit /b
)
copy /y "%LOCALAPPDATA%\ReverseCoin3D\game\uninstall.ps1" "%TEMP%\rcb3d_uninstall.ps1" >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\rcb3d_uninstall.ps1"
del "%TEMP%\rcb3d_uninstall.ps1" >nul 2>&1
pause
