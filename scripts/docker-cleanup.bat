@echo off
echo ========================================
echo AI Agent Orchestration Platform Cleanup
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

echo Docker is running. Continuing cleanup...

echo.

REM Stop and remove containers
echo Stopping and removing containers...
docker-compose down

echo.

REM Remove volumes
echo Removing volumes...
docker-compose down -v

echo.

REM Remove images
echo Removing images...
docker rmi ai_orchestration_backend ai_orchestration_frontend ai_orchestration_postgres ai_orchestration_redis 2>nul

echo.

REM Remove orphaned volumes
echo Removing orphaned volumes...
docker volume prune -f

echo.

REM Remove orphaned networks
echo Removing orphaned networks...
docker network prune -f

echo.

echo Cleanup completed!
echo.
pause