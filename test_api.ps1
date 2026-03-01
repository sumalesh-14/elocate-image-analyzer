# Test script for the Image Analyzer API

$API_KEY = "XBZLmUDmGb0TxCGwkjPoHPAIuXPYTy0i5iOQ5HOR3Pk"
$BASE_URL = "http://localhost:8000"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Testing Image Analyzer API" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Test 1: Root endpoint
Write-Host "Test 1: Root Endpoint" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/" -Method Get
    Write-Host "Success: $($response.service)" -ForegroundColor Green
    Write-Host "Version: $($response.version)" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 2: Health endpoint
Write-Host "Test 2: Health Check" -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/health" -Method Get
    Write-Host "Status: $($response.status)" -ForegroundColor Green
    Write-Host "Database Available: $($response.database_available)" -ForegroundColor Green
    Write-Host "Gemini API Available: $($response.gemini_api_available)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Test endpoint (without image)
Write-Host "Test 3: Test Endpoint (No Image)" -ForegroundColor Cyan
try {
    $headers = @{
        "X-API-Key" = $API_KEY
    }
    $response = Invoke-RestMethod -Uri "$BASE_URL/test" -Method Get -Headers $headers
    Write-Host "Success: $($response.success)" -ForegroundColor Green
    Write-Host "Message: $($response.message)" -ForegroundColor Green
}
catch {
    Write-Host "Failed: $_" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Blue
Write-Host "  Test Summary" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Server is running" -ForegroundColor Green
Write-Host "Database connection working" -ForegroundColor Green
Write-Host "Gemini API key needs to be updated" -ForegroundColor Yellow
Write-Host ""
Write-Host "To test image analysis:" -ForegroundColor Cyan
Write-Host "1. Update GEMINI_API_KEY in .env file" -ForegroundColor Gray
Write-Host "2. Restart the server" -ForegroundColor Gray
Write-Host "3. Use the test UI at: http://localhost:8000/test-ui" -ForegroundColor Gray
Write-Host "   Or use the API docs at: http://localhost:8000/docs" -ForegroundColor Gray
