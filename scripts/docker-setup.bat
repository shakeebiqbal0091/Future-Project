@echo off
echo ========================================
echo AI Agent Orchestration Platform Setup
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

echo Docker is running. Continuing setup...

echo.

REM Copy environment file
if not exist .env (
    echo Copying environment template...
copy .env.example .env
    echo.
    echo ========================================
    echo IMPORTANT: Please edit the .env file with
    echo your configuration before continuing.
    echo ========================================
    notepad .env
) else (
    echo .env file already exists. Skipping copy.
)

echo.

REM Create necessary directories
if not exist backend mkdir backend
if not exist frontend mkdir frontend
if not exist docker mkdir docker
if not exist scripts mkdir scripts
if not exist config mkdir config
if not exist tests mkdir tests

echo.

REM Show next steps
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit the .env file with your configuration
echo 2. Run 'docker-compose up -d' to start all services
echo 3. Run 'docker-compose exec backend python scripts/init_db.py' to initialize the database
echo 4. Access the application:
echo    - Backend: http://localhost:8000
echo    - Frontend: http://localhost:3000
echo.
echo For more information, see the README.md file.
echo.
pause