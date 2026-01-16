# CORS Verification Script
# Run this to verify CORS is working correctly

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "CORS Configuration Verification" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$apiUrl = "https://api.samwylock.com"
$origin = "https://admin.samwylock.com"

# Test 1: Preflight Request (OPTIONS)
Write-Host "[1/3] Testing CORS Preflight Request..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/auth/login" `
        -Method OPTIONS `
        -Headers @{
            "Origin" = $origin
            "Access-Control-Request-Method" = "POST"
            "Access-Control-Request-Headers" = "Content-Type"
        } `
        -UseBasicParsing

    $allowOrigin = $response.Headers["Access-Control-Allow-Origin"]
    $allowMethods = $response.Headers["Access-Control-Allow-Methods"]
    $allowHeaders = $response.Headers["Access-Control-Allow-Headers"]
    $allowCredentials = $response.Headers["Access-Control-Allow-Credentials"]

    if ($allowOrigin -eq $origin) {
        Write-Host "✅ CORS Origin: $allowOrigin" -ForegroundColor Green
    } else {
        Write-Host "❌ CORS Origin: $allowOrigin (expected: $origin)" -ForegroundColor Red
    }

    Write-Host "   Allowed Methods: $allowMethods" -ForegroundColor White
    Write-Host "   Allowed Headers: $allowHeaders" -ForegroundColor White
    Write-Host "   Credentials: $allowCredentials" -ForegroundColor White
} catch {
    Write-Host "❌ Preflight request failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 2: Actual GET Request with Origin
Write-Host "[2/3] Testing GET Request with CORS..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$apiUrl/" `
        -Method GET `
        -Headers @{
            "Origin" = $origin
        } `
        -UseBasicParsing

    $allowOrigin = $response.Headers["Access-Control-Allow-Origin"]

    if ($allowOrigin -eq $origin) {
        Write-Host "✅ GET request successful with CORS" -ForegroundColor Green
        Write-Host "   Response: $($response.Content.Substring(0, [Math]::Min(100, $response.Content.Length)))..." -ForegroundColor White
    } else {
        Write-Host "⚠️  Request succeeded but CORS header incorrect" -ForegroundColor Yellow
        Write-Host "   Expected: $origin" -ForegroundColor White
        Write-Host "   Got: $allowOrigin" -ForegroundColor White
    }
} catch {
    Write-Host "❌ GET request failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Test 3: Check S3 CORS Configuration
Write-Host "[3/3] Checking S3 Bucket CORS..." -ForegroundColor Yellow
try {
    $s3Cors = aws s3api get-bucket-cors --bucket hovver-images-dev --region us-east-1 2>&1

    if ($LASTEXITCODE -eq 0) {
        $corsConfig = $s3Cors | ConvertFrom-Json
        $origins = $corsConfig.CORSRules[0].AllowedOrigins

        if ($origins -contains $origin) {
            Write-Host "✅ S3 CORS includes $origin" -ForegroundColor Green
            Write-Host "   All origins: $($origins -join ', ')" -ForegroundColor White
        } else {
            Write-Host "⚠️  S3 CORS does not include $origin" -ForegroundColor Yellow
            Write-Host "   Current origins: $($origins -join ', ')" -ForegroundColor White
        }
    } else {
        Write-Host "❌ Could not retrieve S3 CORS configuration" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ S3 CORS check failed: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "API URL: $apiUrl" -ForegroundColor White
Write-Host "Frontend Origin: $origin" -ForegroundColor White
Write-Host ""
Write-Host "If all tests passed, your frontend should be able to:" -ForegroundColor Yellow
Write-Host "  ✅ Make API requests without CORS errors" -ForegroundColor White
Write-Host "  ✅ Send credentials (cookies/auth headers)" -ForegroundColor White
Write-Host "  ✅ Access S3 images via presigned URLs" -ForegroundColor White
Write-Host ""
Write-Host "Test from your frontend console:" -ForegroundColor Yellow
Write-Host @"
fetch('$apiUrl/', {
  credentials: 'include'
}).then(r => r.json()).then(console.log);
"@ -ForegroundColor White
Write-Host ""

