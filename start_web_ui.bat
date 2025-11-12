@echo off
echo Starting Mythline Web UI...
echo.

echo [1/2] Starting backend API...
start "Backend API" cmd /k "uvicorn src.ui.web.backend.main:app --reload --port 8080"

echo Waiting for backend to start...
timeout /t 3 /nobreak

echo.
echo [2/2] Starting frontend dev server...
start "Frontend Dev" cmd /k "cd src\ui\web\frontend && npm run dev"

echo.
echo All services started!
echo.
echo ============================================
echo   Mythline Web UI is now running!
echo ============================================
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8080
echo   API Docs:  http://localhost:8080/docs
echo.
echo NOTE: Make sure MCP servers are running separately if needed.
echo.
echo Press any key to exit...
pause > nul
