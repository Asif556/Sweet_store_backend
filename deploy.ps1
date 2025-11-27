# Quick Deploy & Test Script for Sweet Store Backend
# This script helps you deploy and verify the image fix

Write-Host "`n🚀 Sweet Store Backend - Deploy & Test Helper`n" -ForegroundColor Cyan

# Step 1: Check Git Status
Write-Host "Step 1: Checking Git status..." -ForegroundColor Yellow
git status --short

Write-Host "`n"

# Step 2: Show what will be committed
Write-Host "Step 2: Files changed:" -ForegroundColor Yellow
git diff --stat

Write-Host "`n"

# Step 3: Commit changes
$commit = Read-Host "Do you want to commit these changes? (y/n)"
if ($commit -eq "y") {
    Write-Host "`nCommitting changes..." -ForegroundColor Yellow
    git add .
    git commit -m "Fix: Complete base64 image storage and retrieval

- Changed image field from 'image_url' to 'image' for consistency
- Added base64 format validation (must start with 'data:image/')
- Increased MAX_CONTENT_LENGTH to 16MB for large images
- Configured CORS to handle large responses
- Added detailed logging for debugging
- Backward compatible with legacy 'image_url' field names
- Returns complete image data without truncation"
    
    Write-Host "✅ Changes committed!" -ForegroundColor Green
    
    # Step 4: Push to GitHub
    $push = Read-Host "`nPush to GitHub and trigger Render deployment? (y/n)"
    if ($push -eq "y") {
        Write-Host "`nPushing to GitHub..." -ForegroundColor Yellow
        git push origin main
        
        Write-Host "`n✅ Pushed to GitHub!" -ForegroundColor Green
        Write-Host "`nRender will now automatically deploy your changes." -ForegroundColor Cyan
        Write-Host "This usually takes 2-5 minutes.`n" -ForegroundColor Gray
        
        Write-Host "You can monitor the deployment at:" -ForegroundColor Yellow
        Write-Host "https://dashboard.render.com`n" -ForegroundColor Cyan
        
        # Step 5: Wait and Test
        $wait = Read-Host "Wait for deployment and run tests? (y/n)"
        if ($wait -eq "y") {
            Write-Host "`nWaiting 3 minutes for deployment to complete..." -ForegroundColor Yellow
            Start-Sleep -Seconds 180
            
            Write-Host "`nRunning tests on production backend...`n" -ForegroundColor Yellow
            
            # Update test script to use production URL
            $prodUrl = Read-Host "Enter your Render backend URL (e.g., https://your-app.onrender.com)"
            
            Write-Host "`nTesting production backend at: $prodUrl`n" -ForegroundColor Cyan
            
            # Quick health check
            try {
                $response = Invoke-RestMethod -Uri "$prodUrl/sweets" -Method GET -ErrorAction Stop
                Write-Host "✅ Backend is live and responding!" -ForegroundColor Green
                Write-Host "   Found $($response.Count) sweet(s) in database`n" -ForegroundColor Gray
                
                if ($response.Count -gt 0 -and $response[0].image) {
                    Write-Host "✅ Images are being returned!" -ForegroundColor Green
                    Write-Host "   First sweet: $($response[0].name)" -ForegroundColor Gray
                    Write-Host "   Image length: $($response[0].image.Length) characters" -ForegroundColor Gray
                    Write-Host "   Valid base64: $($response[0].image.StartsWith('data:image/'))`n" -ForegroundColor Gray
                }
            } catch {
                Write-Host "❌ Backend is not responding yet" -ForegroundColor Red
                Write-Host "   It may still be deploying. Check Render dashboard.`n" -ForegroundColor Yellow
            }
        }
    }
} else {
    Write-Host "`nCommit cancelled. Changes not pushed." -ForegroundColor Yellow
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Check Render Dashboard:" -ForegroundColor Yellow
Write-Host "   https://dashboard.render.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. View Deployment Logs:" -ForegroundColor Yellow
Write-Host "   Look for successful deployment message" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Test Your Backend:" -ForegroundColor Yellow
Write-Host "   .\test_image_api.ps1" -ForegroundColor Cyan
Write-Host "   (Update the URL in the script first)" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Test Your Frontend:" -ForegroundColor Yellow
Write-Host "   - Open your React app" -ForegroundColor Gray
Write-Host "   - Try uploading a sweet with an image" -ForegroundColor Gray
Write-Host "   - Verify image displays correctly" -ForegroundColor Gray
Write-Host ""
Write-Host "5. Check Logs:" -ForegroundColor Yellow
Write-Host "   Look for these messages:" -ForegroundColor Gray
Write-Host "   📸 Storing image... (when adding)" -ForegroundColor Gray
Write-Host "   📤 Returning X sweet(s)... (when fetching)" -ForegroundColor Gray
Write-Host ""
Write-Host "========================================`n" -ForegroundColor Cyan

Write-Host "For detailed information, see:" -ForegroundColor Yellow
Write-Host "IMAGE_FIX_SUMMARY.md`n" -ForegroundColor Cyan
