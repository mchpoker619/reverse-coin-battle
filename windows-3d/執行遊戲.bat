@echo off
rem Reverse Coin Battle 3D - offline launcher (test promo version, not for sale)
cd /d "%~dp0"
set "GAME=%~dp0game\ReverseCoin3D.html"
if not exist "%GAME%" (
  echo [ERROR] game\ReverseCoin3D.html not found. Please unzip the whole folder first.
  pause
  exit /b
)
set "BROWSER="
for %%E in (msedge.exe chrome.exe) do (
  for %%K in (HKLM HKCU) do (
    if not defined BROWSER (
      for /f "tokens=2,*" %%A in ('reg query "%%K\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\%%E" /ve 2^>nul ^| find "REG_SZ"') do (
        if exist "%%~B" set "BROWSER=%%~B"
      )
    )
  )
)
if defined BROWSER (
  rem App window: no address bar, looks like a normal program
  start "" "%BROWSER%" --app="file:///%GAME%" --start-maximized
) else (
  start "" "%GAME%"
)
