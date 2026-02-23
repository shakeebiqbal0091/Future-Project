#!/bin/bash

echo "====================================="
echo "AI Agent Orchestration Platform Cleanup"
echo "====================================="
echo

# Check if Docker is running
echo "Checking Docker status..."
docker info >/dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "Docker is running. Continuing cleanup..."
echo

# Stop and remove containers
echo "Stopping and removing containers..."
docker-compose down

echo

# Remove volumes
echo "Removing volumes..."
docker-compose down -v

echo

# Remove images
echo "Removing images..."
docker rmi ai_orchestration_backend ai_orchestration_frontend ai_orchestration_postgres ai_orchestration_redis 2>/dev/null

echo

# Remove orphaned volumes
echo "Removing orphaned volumes..."
docker volume prune -f

echo

# Remove orphaned networks
echo "Removing orphaned networks..."
docker network prune -f

echo

echo "Cleanup completed!"
echo