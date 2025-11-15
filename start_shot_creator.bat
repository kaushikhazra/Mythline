@echo off
echo ========================================
echo Shot Creator
echo ========================================
echo.

if "%1"=="" (
    echo Usage: start_shot_creator.bat [subject]
    echo.
    echo Example:
    echo   start_shot_creator.bat Sarephine
    echo.
    pause
    exit /b 1
)

python -m src.ui.cli.create_shots --subject %1
pause
