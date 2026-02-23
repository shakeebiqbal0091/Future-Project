#!/bin/bash

echo "====================================="
echo "AI Agent Orchestration Platform Setup"
echo "====================================="
echo

# Check if Docker is running
echo "Checking Docker status..."
docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "Docker is running. Continuing setup..."
echo

# Copy environment file
if [ ! -f .env ]; then
    echo "Copying environment template..."
    cp .env.example .env
    echo
    echo "====================================="
    echo "IMPORTANT: Please edit the .env file with"
    echo "your configuration before continuing."
    echo "====================================="
    nano .env
else
    echo ".env file already exists. Skipping copy."
fi

echo

# Create necessary directories
mkdir -p backend frontend docker/backend docker/frontend docker/postgres docker/redis scripts config tests

echo

echo "====================================="
echo "Setup Complete!"
echo "====================================="
echo
echo "Next steps:"
echo "1. Edit the .env file with your configuration"
echo "2. Run 'docker-compose up -d' to start all services"
echo "3. Run 'docker-compose exec backend python scripts/init_db.py' to initialize the database"
echo "4. Access the application:"
echo "   - Backend: http://localhost:8000"
echo "   - Frontend: http://localhost:3000"
echo
echo "For more information, see the README.md file."
echo