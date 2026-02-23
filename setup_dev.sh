#!/bin/bash
# AI Agent Orchestration Platform - Development Setup Script
# This script sets up the complete development environment
set -e

echo "🚀 Setting up AI Agent Orchestration Platform development environment..."

# Check if Docker is installed
if ! command -v docker \u0026\u0026 ! command -v docker-compose \u0026; then
    echo "❌ Docker is not installed. Please install Docker Desktop first:"
    echo "   https://www.docker.com/products/docker-desktop/"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node \u0026\u0026 ! command -v npm \u0026; then
    echo "❌ Node.js is not installed. Please install Node.js first:"
    echo "   https://nodejs.org/"
    exit 1
fi

# Check if Python is installed
if ! command -v python \u0026\u0026 ! command -v python3 \u0026; then
    echo "❌ Python is not installed. Please install Python 3.11+ first:"
    echo "   https://www.python.org/downloads/"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "🖏 Creating .env file from example..."
    cp .env.example .env
    
    # Set up development defaults
    sed -i "s/ENVIRONMENT=production/ENVIRONMENT=development/g" .env
    sed -i "s/DEBUG=false/DEBUG=true/g" .env
    
    echo "✅ .env file created successfully"
else
    echo "✅ .env file already exists"
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
python -m pip install -r requirements.txt

echo "✅ Python dependencies installed"

# Install Node.js dependencies
echo "📦 Installing Node.js dependencies..."
cd frontend
npm install
cd ..
echo "✅ Node.js dependencies installed"

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p uploads logs data
echo "✅ Directories created"

# Check if Docker containers are running
echo "🌐 Checking Docker services..."

# Stop existing containers if running
docker-compose down 2>/dev/null || true

# Start all services
echo "🚀 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are running
echo "🐝 Verifying services are running..."

# Check PostgreSQL
if docker-compose ps postgres | grep -q "Up"; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL failed to start"
    exit 1
fi

# Check Redis
if docker-compose ps redis | grep -q "Up"; then
    echo "✅ Redis is running"
else
    echo "❌ Redis failed to start"
    exit 1
fi

# Check Backend
if docker-compose ps backend | grep -q "Up"; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start"
    exit 1
fi

# Check Frontend
if docker-compose ps frontend | grep -q "Up"; then
    echo "✅ Frontend is running"
else
    echo "❌ Frontend failed to start"
    exit 1
fi

# Check Celery services
if docker-compose ps celery_worker | grep -q "Up"; then
    echo "✅ Celery worker is running"
fi

if docker-compose ps celery_beat | grep -q "Up"; then
    echo "✅ Celery beat is running"
fi

echo "✅ All services are running!"

# Run database migrations
echo "🗐 Running database migrations..."
cd backend
python -c "from app.core.database import create_all_tables; create_all_tables()"
cd ..
echo "✅ Database migrations completed"

# Run tests to verify setup
echo "🦚 Running tests to verify setup..."
cd backend
python run_tests.py
cd ..
echo "✅ Tests completed"

echo ""
echo "🎉 AI Agent Orchestration Platform development environment setup complete!"
echo ""
echo "📍 Services are running:"
echo "   📡 Backend API: http://localhost:8000"
echo "   🌐 Frontend: http://localhost:3000"
echo "   🗄️ PostgreSQL: localhost:5432"
echo "   ⭕ Redis: localhost:6379"
echo ""
echo "💡 Useful commands:"
echo "   🐳 View logs: docker-compose logs -f [service_name]"
echo "   ⏹️ Stop services: docker-compose down"
echo "   🚀 Restart services: docker-compose restart"
echo "   🦚 Run tests: cd backend && python run_tests.py"
echo ""
echo "󛢙 Development workflow:"
echo "   1. Make changes to code"
echo "   2. Services auto-reload"
echo "   3. Test in browser"
echo "   4. Run tests"
echo "   5. Commit changes"
