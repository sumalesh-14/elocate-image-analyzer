#!/bin/bash

# Deployment script for elocate-image-analyzer
# This script helps deploy the application to Railway or Docker

set -e  # Exit on error

echo "=========================================="
echo "  ELocate Image Analyzer Deployment"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "Please create a .env file with required environment variables."
    exit 1
fi

print_success ".env file found"

# Run database connection test
print_info "Running database connection test..."
python test_local_db.py

if [ $? -ne 0 ]; then
    print_error "Database connection test failed!"
    echo "Please fix database connection issues before deploying."
    exit 1
fi

print_success "Database connection test passed"
echo ""

# Ask user for deployment method
echo "Select deployment method:"
echo "1) Railway (recommended)"
echo "2) Docker"
echo "3) Run tests only (no deployment)"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        print_info "Preparing Railway deployment..."
        
        # Check if railway CLI is installed
        if ! command -v railway &> /dev/null; then
            print_warning "Railway CLI not found"
            echo "Install it with: npm i -g @railway/cli"
            echo "Or deploy via GitHub integration at: https://railway.app"
            exit 1
        fi
        
        # Check if logged in
        print_info "Checking Railway authentication..."
        railway whoami &> /dev/null
        
        if [ $? -ne 0 ]; then
            print_warning "Not logged in to Railway"
            echo "Run: railway login"
            exit 1
        fi
        
        print_success "Railway CLI ready"
        
        # Deploy
        print_info "Deploying to Railway..."
        railway up
        
        print_success "Deployment initiated!"
        echo ""
        echo "Check deployment status:"
        echo "  railway status"
        echo ""
        echo "View logs:"
        echo "  railway logs"
        ;;
        
    2)
        print_info "Building Docker image..."
        
        # Build Docker image
        docker build -t elocate-image-analyzer:latest .
        
        if [ $? -ne 0 ]; then
            print_error "Docker build failed!"
            exit 1
        fi
        
        print_success "Docker image built successfully"
        
        # Ask if user wants to run it
        read -p "Run container now? [y/N]: " run_container
        
        if [[ $run_container =~ ^[Yy]$ ]]; then
            print_info "Starting container on port 8000..."
            docker run -d -p 8000:8000 --env-file .env --name elocate-analyzer elocate-image-analyzer:latest
            
            print_success "Container started!"
            echo ""
            echo "Test the service:"
            echo "  curl http://localhost:8000/health"
            echo ""
            echo "View logs:"
            echo "  docker logs -f elocate-analyzer"
            echo ""
            echo "Stop container:"
            echo "  docker stop elocate-analyzer"
        fi
        ;;
        
    3)
        print_info "Running comprehensive tests..."
        
        # Run pytest if available
        if command -v pytest &> /dev/null; then
            pytest tests/ -v
            print_success "All tests completed"
        else
            print_warning "pytest not found, skipping unit tests"
        fi
        ;;
        
    *)
        print_error "Invalid choice"
        exit 1
        ;;
esac

echo ""
print_success "Deployment process completed!"
echo ""
echo "Next steps:"
echo "1. Verify health endpoint: curl https://your-app.railway.app/health"
echo "2. Test database connection: curl https://your-app.railway.app/api/v1/health/db"
echo "3. Monitor logs for any issues"
echo "4. Update frontend with new API URL"
