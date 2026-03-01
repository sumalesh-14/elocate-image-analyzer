# PowerShell Deployment script for elocate-image-analyzer
# This script helps deploy the application to Railway or Docker

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Blue
Write-Host "  ELocate Image Analyzer Deployment" -ForegroundColor Blue
Write-Host "==========================================" -ForegroundColor Blue
Write-Host ""

function Print-Success {
    param($Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Print-Info {
    param($Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Print-Warning {
    param($Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

function Print-Error {
    param($Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

# Check if .env file exists
if (-not (Test-Path .env)) {
    Print-Error ".env file not found!"
    Write-Host "Please create a .env file with required environment variables."
    exit 1
}

Print-Success ".env file found"

# Run database connection test
Print-Info "Running database connection test..."
python test_local_db.py

if ($LASTEXITCODE -ne 0) {
    Print-Error "Database connection test failed!"
    Write-Host "Please fix database connection issues before deploying."
    exit 1
}

Print-Success "Database connection test passed"
Write-Host ""

# Ask user for deployment method
Write-Host "Select deployment method:"
Write-Host "1) Railway (recommended)"
Write-Host "2) Docker"
Write-Host "3) Run tests only (no deployment)"
$choice = Read-Host "Enter choice [1-3]"

switch ($choice) {
    "1" {
        Print-Info "Preparing Railway deployment..."
        
        # Check if railway CLI is installed
        $railwayCmd = Get-Command railway -ErrorAction SilentlyContinue
        
        if (-not $railwayCmd) {
            Print-Warning "Railway CLI not found"
            Write-Host "Install it with: npm i -g @railway/cli"
            Write-Host "Or deploy via GitHub integration at: https://railway.app"
            exit 1
        }
        
        # Check if logged in
        Print-Info "Checking Railway authentication..."
        railway whoami 2>&1 | Out-Null
        
        if ($LASTEXITCODE -ne 0) {
            Print-Warning "Not logged in to Railway"
            Write-Host "Run: railway login"
            exit 1
        }
        
        Print-Success "Railway CLI ready"
        
        # Deploy
        Print-Info "Deploying to Railway..."
        railway up
        
        Print-Success "Deployment initiated!"
        Write-Host ""
        Write-Host "Check deployment status:"
        Write-Host "  railway status"
        Write-Host ""
        Write-Host "View logs:"
        Write-Host "  railway logs"
    }
    
    "2" {
        Print-Info "Building Docker image..."
        
        # Build Docker image
        docker build -t elocate-image-analyzer:latest .
        
        if ($LASTEXITCODE -ne 0) {
            Print-Error "Docker build failed!"
            exit 1
        }
        
        Print-Success "Docker image built successfully"
        
        # Ask if user wants to run it
        $runContainer = Read-Host "Run container now? [y/N]"
        
        if ($runContainer -match "^[Yy]$") {
            Print-Info "Starting container on port 8000..."
            docker run -d -p 8000:8000 --env-file .env --name elocate-analyzer elocate-image-analyzer:latest
            
            Print-Success "Container started!"
            Write-Host ""
            Write-Host "Test the service:"
            Write-Host "  curl http://localhost:8000/health"
            Write-Host ""
            Write-Host "View logs:"
            Write-Host "  docker logs -f elocate-analyzer"
            Write-Host ""
            Write-Host "Stop container:"
            Write-Host "  docker stop elocate-analyzer"
        }
    }
    
    "3" {
        Print-Info "Running comprehensive tests..."
        
        # Run pytest if available
        $pytestCmd = Get-Command pytest -ErrorAction SilentlyContinue
        
        if ($pytestCmd) {
            pytest tests/ -v
            Print-Success "All tests completed"
        } else {
            Print-Warning "pytest not found, skipping unit tests"
        }
    }
    
    default {
        Print-Error "Invalid choice"
        exit 1
    }
}

Write-Host ""
Print-Success "Deployment process completed!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Verify health endpoint: curl https://your-app.railway.app/health"
Write-Host "2. Test database connection: curl https://your-app.railway.app/api/v1/health/db"
Write-Host "3. Monitor logs for any issues"
Write-Host "4. Update frontend with new API URL"
