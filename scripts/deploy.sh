#!/bin/bash

# ============================================
# RICKQUEUE DEPLOYMENT SCRIPT
# ============================================

set -e  # Exit on error

echo "🚀 RickQueue Deployment Script"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "Please create .env from .env.example"
    exit 1
fi

print_status ".env file found"

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check deployment target
DEPLOY_TARGET=${1:-local}

case $DEPLOY_TARGET in
    local)
        echo ""
        echo "📦 Deploying to LOCAL (Docker Compose)"
        echo "================================"
        
        # Check if Docker is running
        if ! docker info > /dev/null 2>&1; then
            print_error "Docker is not running!"
            exit 1
        fi
        print_status "Docker is running"
        
        # Build and start containers
        print_status "Building containers..."
        docker-compose build
        
        print_status "Starting services..."
        docker-compose up -d
        
        # Wait for services to be healthy
        print_status "Waiting for services to be ready..."
        sleep 10
        
        # Check health
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Backend is healthy!"
            echo ""
            echo "✅ Deployment complete!"
            echo ""
            echo "📍 API: http://localhost:8000"
            echo "📍 Docs: http://localhost:8000/docs"
            echo "📍 pgAdmin: http://localhost:5050 (if tools profile enabled)"
            echo ""
            echo "View logs: docker-compose logs -f backend"
        else
            print_error "Health check failed!"
            echo "Check logs: docker-compose logs backend"
            exit 1
        fi
        ;;
        
    railway)
        echo ""
        echo "🚂 Deploying to RAILWAY"
        echo "================================"
        
        # Check if Railway CLI is installed
        if ! command -v railway &> /dev/null; then
            print_error "Railway CLI not found!"
            echo "Install: npm i -g @railway/cli"
            exit 1
        fi
        print_status "Railway CLI found"
        
        # Login check
        if ! railway whoami > /dev/null 2>&1; then
            print_warning "Not logged in to Railway"
            railway login
        fi
        print_status "Logged in to Railway"
        
        # Deploy
        print_status "Deploying to Railway..."
        railway up
        
        print_status "Running migrations..."
        railway run alembic upgrade head
        
        echo ""
        echo "✅ Deployment to Railway complete!"
        echo ""
        echo "View your app: railway open"
        echo "View logs: railway logs"
        ;;
        
    render)
        echo ""
        echo "🎨 Deploying to RENDER"
        echo "================================"
        
        print_warning "Render deployment requires manual setup"
        echo ""
        echo "Steps:"
        echo "1. Push code to GitHub"
        echo "2. Create new Web Service on Render"
        echo "3. Connect GitHub repo"
        echo "4. Set environment variables from .env"
        echo "5. Deploy!"
        echo ""
        echo "Build Command: pip install -r requirements.txt"
        echo "Start Command: alembic upgrade head && uvicorn app.main:socket_app --host 0.0.0.0 --port \$PORT"
        ;;
        
    *)
        print_error "Unknown deployment target: $DEPLOY_TARGET"
        echo ""
        echo "Usage: ./deploy.sh [local|railway|render]"
        echo ""
        echo "Examples:"
        echo "  ./deploy.sh local    - Deploy with Docker Compose"
        echo "  ./deploy.sh railway  - Deploy to Railway"
        echo "  ./deploy.sh render   - Show Render deployment instructions"
        exit 1
        ;;
esac