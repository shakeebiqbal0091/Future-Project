@echo off
echo ========================================
echo AI Agent Orchestration Platform Commands
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

echo Docker is running. Available commands:

echo.

echo 1. Start all services
docker-compose up -d
echo.

echo 2. Stop all services
docker-compose down
echo.

echo 3. View logs
docker-compose logs -f
echo.

echo 4. Access backend shell
docker-compose exec backend sh
echo.

echo 5. Access frontend shell
docker-compose exec frontend sh
echo.

echo 6. Access database shell
docker-compose exec postgres psql -U postgres -d ai_orchestration
echo.

echo 7. Run tests
docker-compose exec backend pytest
echo.

echo 8. Initialize database
docker-compose exec backend python scripts/init_db.py
echo.

echo 9. Show service status
docker-compose ps
echo.

echo 10. Cleanup
echo   a. docker-cleanup.bat
echo   b. docker-compose down -v
echo.
pause