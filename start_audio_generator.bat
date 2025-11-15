@echo off
echo ========================================
echo Audio Generator
echo ========================================
echo.

if "%1"=="" (
    echo Usage: start_audio_generator.bat [subject]
    echo.
    echo Example:
    echo   start_audio_generator.bat shadowglen
    echo.
    pause
    exit /b 1
)

python -m src.ui.cli.create_audio --subject %1
pause
