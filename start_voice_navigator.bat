@echo off
echo ========================================
echo Voice Navigator
echo ========================================
echo.

if "%1"=="" (
    echo Usage: start_voice_navigator.bat [subject]
    echo.
    echo Example:
    echo   start_voice_navigator.bat last_stand
    echo.
    pause
    exit /b 1
)

python -m src.ui.cli.voice_navigator %1
