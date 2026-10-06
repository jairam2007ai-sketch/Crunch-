@echo off
setlocal
title Crunch Business Manager
cd /d "%~dp0"

echo.
echo   Customize Your Crunch - starting up
echo   -----------------------------------

rem 1. Python server (first run creates it)
if not exist "backend\.venv\Scripts\python.exe" (
  echo   Setting up the server for the first time. This takes a minute or two...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv backend\.venv
  ) else (
    python -m venv backend\.venv
  )
)
if not exist "backend\.venv\Scripts\python.exe" goto nopython
echo   Checking server packages...
"backend\.venv\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r backend\requirements.txt
if errorlevel 1 goto fail

rem 2. The three websites
where npm >nul 2>nul
if errorlevel 1 goto nonode
pushd frontend
if not exist "node_modules" (
  echo   Installing website packages. This takes a minute...
  call npm install --no-audit --no-fund
  if errorlevel 1 goto failpop
)
echo   Building the websites...
call npm run build --silent >nul
if errorlevel 1 goto failpop
popd

rem 3. Database and menu (the admin site asks for your owner account the first time)
pushd backend
".venv\Scripts\python.exe" -m app.cli setup
if errorlevel 1 goto failpop

rem 4. Run, and open the browser
".venv\Scripts\python.exe" -m app.run
if errorlevel 1 goto failpop
popd
goto end

:nopython
echo.
echo   Python isn't installed. Get it from https://www.python.org/downloads/
echo   (tick "Add python.exe to PATH" while installing), then run start.bat again.
goto stop

:nonode
echo.
echo   Node.js isn't installed. Get the LTS version from https://nodejs.org/
echo   then run start.bat again.
goto stop

:failpop
popd
:fail
echo.
echo   Something went wrong (see the message above). Fix it and run start.bat again.
echo   If it says the port is already in use, close the other Crunch window first.
goto stop

:stop
echo.
pause
exit /b 1

:end
endlocal
