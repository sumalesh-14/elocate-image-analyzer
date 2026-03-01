# Test script for Railway deployed API

$RAILWAY_URL = "https://elocate-python-production.up.railway.app"
$API_KEY = "XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Testing Railway Deployment" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "URL: $RAILWAY_URL" -ForegroundColor Cyan
Write-Host ""

# Test 1: Root endpoint
Write-Host "Test 1: Root Endpoint" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$RAILWAY_URL/" -Method Get -TimeoutSec 10
    Write-Host "Success: $($response.service)" -ForegroundColor Green
    Write-Host "Version: $($response.version)" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 2: Health endpoint
Write-Host "Test 2: Health Check" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$RAILWAY_URL/health" -Method Get -TimeoutSec 10
    Write-Host "Status: $($response.status)" -ForegroundColor Green
    Write-Host "Database Available: $($response.database_available)" -ForegroundColor Green
    Write-Host "Gemini API Available: $($response.gemini_api_available)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Yellow
    }
}
Write-Host ""

# Test 3: Test endpoint (with API key)
Write-Host "Test 3: Test Endpoint (With API Key)" -ForegroundColor Cyan
try {
    $headers = @{
        "X-API-Key" = $API_KEY
    }
    $response = Invoke-RestMethod -Uri "$RAILWAY_URL/test" -Method Get -Headers $headers -TimeoutSec 10
    Write-Host "Success: $($response.success)" -ForegroundColor Green
    Write-Host "Message: $($response.message)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 4: API Documentation
Write-Host "Test 4: API Documentation" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$RAILWAY_URL/docs" -Method Get -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "API Docs available" -ForegroundColor Green
    }
}
catch {
    Write-Host "Failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Test Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Railway URL: $RAILWAY_URL" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. If tests pass, your API is ready to use"
Write-Host "2. Update frontend with Railway URL"
Write-Host "3. Test image upload from frontend"
Write-Host "4. Monitor logs: railway logs"
Write-Host ""
Write-Host "Useful Links:" -ForegroundColor Yellow
Write-Host "API Docs: $RAILWAY_URL/docs"
Write-Host "Test UI: $RAILWAY_URL/test-ui"
Write-Host "Health: $RAILWAY_URL/health"
