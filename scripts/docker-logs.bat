@echo off
echo ========================================
echo AI Agent Orchestration Platform Logs
echo ========================================
echo.

REM Check if Docker is running
echo Checking Docker status...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Docker is running. Showing logs...

echo.

REM Show all logs
docker-compose logs -f

echo.
pause