@echo off
python -m src.ui.cli.create_story %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Story generation failed. See error above.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo Success!
pause
