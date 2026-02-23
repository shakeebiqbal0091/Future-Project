#!/bin/bash

echo "====================================="
echo "AI Agent Orchestration Platform Commands"
echo "====================================="
echo

# Check if Docker is running
echo "Checking Docker status..."
docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "Docker is running. Available commands:"
echo

echo "1. Start all services"
echo "   docker-compose up -d"
echo

echo "2. Stop all services"
echo "   docker-compose down"
echo

echo "3. View logs"
echo "   docker-compose logs -f"
echo

echo "4. Access backend shell"
echo "   docker-compose exec backend sh"
echo

echo "5. Access frontend shell"
echo "   docker-compose exec frontend sh"
echo

echo "6. Access database shell"
echo "   docker-compose exec postgres psql -U postgres -d ai_orchestration"
echo

echo "7. Run tests"
echo "   docker-compose exec backend pytest"
echo

echo "8. Initialize database"
echo "   docker-compose exec backend python scripts/init_db.py"
echo

echo "9. Show service status"
echo "   docker-compose ps"
echo

echo "10. Cleanup"
echo "    a. ./scripts/docker-cleanup.sh"
echo "    b. docker-compose down -v"
echo