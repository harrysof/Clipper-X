@echo off
title Clipper X
cd /d "%~dp0"

echo.
echo  ===========================
echo   Clipper X
echo  ===========================
echo.

py -3.12 main.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Something went wrong.
    pause
    exit /b 1
)

pause