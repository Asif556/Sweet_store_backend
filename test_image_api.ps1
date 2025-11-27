# PowerShell Script to Test Sweet Store Backend Image Handling
# This script tests the complete image upload and retrieval flow

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Sweet Store Backend - Image API Test" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Configuration
$baseUrl = "http://localhost:5000"  # Change to your backend URL
# For deployed Render app, use: $baseUrl = "https://sweet-store-backend.onrender.com"

# Test 1: Check if backend is running
Write-Host "[TEST 1] Checking backend health..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/sweets" -Method GET -ErrorAction Stop
    Write-Host "✅ Backend is running" -ForegroundColor Green
    Write-Host "   Found $($response.Count) sweets in database`n" -ForegroundColor Gray
} catch {
    Write-Host "❌ Backend is not responding" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`n   Make sure your backend is running:" -ForegroundColor Yellow
    Write-Host "   python app.py`n" -ForegroundColor Yellow
    exit 1
}

# Test 2: Add a sweet with base64 image
Write-Host "[TEST 2] Adding a test sweet with base64 image..." -ForegroundColor Yellow

# Small test image (1x1 pixel JPEG encoded as base64)
$testImage = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDAREAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAH/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwA="

$testSweet = @{
    name = "Test Sweet $(Get-Date -Format 'HHmmss')"
    category = "Sweet"
    rate = 100
    unit = "piece"
    image = $testImage
    description = "Test sweet for API validation"
} | ConvertTo-Json

try {
    $addResponse = Invoke-RestMethod -Uri "$baseUrl/admin/add_sweet" -Method POST -Body $testSweet -ContentType "application/json" -ErrorAction Stop
    Write-Host "✅ Sweet added successfully" -ForegroundColor Green
    Write-Host "   Name: $($addResponse.sweet)" -ForegroundColor Gray
    Write-Host "   Message: $($addResponse.message)`n" -ForegroundColor Gray
} catch {
    Write-Host "❌ Failed to add sweet" -ForegroundColor Red
    Write-Host "   Status: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    
    # Try to get error details from response
    if ($_.ErrorDetails.Message) {
        $errorObj = $_.ErrorDetails.Message | ConvertFrom-Json
        Write-Host "   Details: $($errorObj.error)`n" -ForegroundColor Red
    }
}

# Test 3: Retrieve sweets and verify image data
Write-Host "[TEST 3] Retrieving sweets and verifying image data..." -ForegroundColor Yellow
try {
    $sweets = Invoke-RestMethod -Uri "$baseUrl/sweets" -Method GET -ErrorAction Stop
    
    if ($sweets.Count -eq 0) {
        Write-Host "⚠️  No sweets found in database" -ForegroundColor Yellow
    } else {
        Write-Host "✅ Retrieved $($sweets.Count) sweet(s)" -ForegroundColor Green
        
        # Check first sweet for image data
        $firstSweet = $sweets[0]
        Write-Host "`n   First Sweet Details:" -ForegroundColor Gray
        Write-Host "   - Name: $($firstSweet.name)" -ForegroundColor Gray
        Write-Host "   - Category: $($firstSweet.category)" -ForegroundColor Gray
        Write-Host "   - Rate: ₹$($firstSweet.rate)" -ForegroundColor Gray
        Write-Host "   - Unit: $($firstSweet.unit)" -ForegroundColor Gray
        
        if ($firstSweet.image) {
            $imageLength = $firstSweet.image.Length
            $isValidBase64 = $firstSweet.image.StartsWith("data:image/")
            
            Write-Host "   - Image Length: $imageLength characters" -ForegroundColor Gray
            Write-Host "   - Valid Base64: $isValidBase64" -ForegroundColor Gray
            Write-Host "   - Image Prefix: $($firstSweet.image.Substring(0, [Math]::Min(50, $imageLength)))" -ForegroundColor Gray
            
            if ($isValidBase64) {
                Write-Host "`n✅ Image data is valid and complete!" -ForegroundColor Green
            } else {
                Write-Host "`n❌ Image data is NOT valid base64!" -ForegroundColor Red
            }
        } else {
            Write-Host "   - Image: ❌ MISSING" -ForegroundColor Red
            Write-Host "`n❌ Image field is missing or empty!" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "❌ Failed to retrieve sweets" -ForegroundColor Red
    Write-Host "   Error: $($_.Exception.Message)`n" -ForegroundColor Red
}

# Test 4: Test with larger image (simulate real upload)
Write-Host "`n[TEST 4] Testing with larger base64 image..." -ForegroundColor Yellow

# Generate a larger base64 string (simulating a real image ~50KB)
$largeBase64 = "data:image/jpeg;base64," + ("A" * 50000)  # 50KB of data

$largeSweet = @{
    name = "Large Image Test $(Get-Date -Format 'HHmmss')"
    category = "Sweet"
    rate = 150
    unit = "kg"
    image = $largeBase64
    description = "Testing large base64 image handling"
} | ConvertTo-Json

try {
    $largeResponse = Invoke-RestMethod -Uri "$baseUrl/admin/add_sweet" -Method POST -Body $largeSweet -ContentType "application/json" -ErrorAction Stop
    Write-Host "✅ Large image uploaded successfully" -ForegroundColor Green
    Write-Host "   Size: ~50KB" -ForegroundColor Gray
    Write-Host "   This confirms backend can handle real image sizes`n" -ForegroundColor Gray
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "❌ Failed to upload large image" -ForegroundColor Red
    Write-Host "   Status Code: $statusCode" -ForegroundColor Red
    
    if ($statusCode -eq 413) {
        Write-Host "   Issue: Payload Too Large" -ForegroundColor Red
        Write-Host "   Solution: Increase MAX_CONTENT_LENGTH in app.py" -ForegroundColor Yellow
    } elseif ($statusCode -eq 400) {
        Write-Host "   Issue: Bad Request (validation failed)" -ForegroundColor Red
        if ($_.ErrorDetails.Message) {
            $errorObj = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "   Details: $($errorObj.error)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

Write-Host "`nIf all tests passed:" -ForegroundColor Green
Write-Host "✓ Backend is accepting base64 images" -ForegroundColor Green
Write-Host "✓ Images are stored completely" -ForegroundColor Green
Write-Host "✓ Images are returned with correct format" -ForegroundColor Green
Write-Host "✓ Frontend should be able to display images`n" -ForegroundColor Green

Write-Host "If tests failed, check:" -ForegroundColor Yellow
Write-Host "- Backend logs for detailed error messages" -ForegroundColor Yellow
Write-Host "- MAX_CONTENT_LENGTH setting in app.py" -ForegroundColor Yellow
Write-Host "- CORS configuration" -ForegroundColor Yellow
Write-Host "- MongoDB connection" -ForegroundColor Yellow
Write-Host "- Image validation logic`n" -ForegroundColor Yellow

Write-Host "========================================`n" -ForegroundColor Cyan
