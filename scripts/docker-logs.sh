#!/bin/bash

echo "====================================="
echo "AI Agent Orchestration Platform Logs"
echo "====================================="
echo

# Check if Docker is running
echo "Checking Docker status..."
docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "Docker is running. Showing logs..."
echo

# Show all logs
docker-compose logs -f
echo