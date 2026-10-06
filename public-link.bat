@echo off
setlocal
title Crunch - public link
set "CF=%LOCALAPPDATA%\crunch\cloudflared.exe"

echo.
echo   Customize Your Crunch - public link
echo   -----------------------------------
if not exist "%CF%" goto download
goto check

:download
echo   Downloading Cloudflare's free tunnel tool. One time only, about 60 MB...
if not exist "%LOCALAPPDATA%\crunch" mkdir "%LOCALAPPDATA%\crunch"
curl -L -o "%CF%" https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe
if errorlevel 1 goto fail

:check
curl -s -m 2 http://127.0.0.1:8000/api/health >nul 2>nul
if errorlevel 1 goto notrunning

echo.
echo   Your public link appears below, ending in .trycloudflare.com
echo   Buyers:  the link itself
echo   Sellers: the link + /seller/
echo   Owner:   the link + /admin/
echo   It works while this window and start.bat stay open. You get a new link each time.
echo.
"%CF%" tunnel --protocol http2 --url http://127.0.0.1:8000 --no-autoupdate
goto end

:notrunning
echo.
echo   The Crunch server isn't running. Double-click start.bat first, then run this again.
goto stop

:fail
echo.
echo   The download didn't work. Check your internet connection and try again.

:stop
echo.
pause
exit /b 1

:end
endlocal
