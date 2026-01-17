# Enable CORS for Localhost - Quick Deployment Script

Write-Host "🌐 Enabling CORS for Localhost Testing" -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host ""

# Check if in terraform directory
$currentPath = Get-Location
if (!(Test-Path "terraform.tfvars")) {
    Write-Host "⚠️  Not in terraform directory. Changing to terraform directory..." -ForegroundColor Yellow
    Set-Location "$PSScriptRoot\terraform"
}

Write-Host "📝 Current CORS Configuration:" -ForegroundColor Green
Write-Host ""
Get-Content terraform.tfvars | Select-String "cors_origins" -Context 0,5
Write-Host ""

Write-Host "🔍 Planning Terraform changes..." -ForegroundColor Yellow
terraform plan -out=tfplan

Write-Host ""
Write-Host "📋 Review Summary:" -ForegroundColor Cyan
Write-Host "  - Adding http://localhost:3000 to CORS origins"
Write-Host "  - Adding http://localhost:5173 to CORS origins"
Write-Host "  - Will update ECS task definition"
Write-Host "  - Will trigger new deployment (2-3 minutes)"
Write-Host ""

$confirm = Read-Host "Do you want to apply these changes? (yes/no)"

if ($confirm -eq "yes" -or $confirm -eq "y") {
    Write-Host ""
    Write-Host "🚀 Applying changes..." -ForegroundColor Green
    terraform apply tfplan

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ CORS configuration updated successfully!" -ForegroundColor Green
        Write-Host ""
        Write-Host "⏳ Waiting for ECS deployment to complete..." -ForegroundColor Yellow
        Write-Host "   This typically takes 2-3 minutes..."
        Write-Host ""

        # Wait a bit for deployment to start
        Start-Sleep -Seconds 10

        Write-Host "📊 Checking deployment status..." -ForegroundColor Cyan
        aws ecs describe-services --cluster hovver-admin-cluster --services hovver-admin-service --query 'services[0].deployments[*].[status,desiredCount,runningCount]' --output table

        Write-Host ""
        Write-Host "🧪 Test CORS from your browser console:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "fetch('https://api.samwylock.com/')" -ForegroundColor White
        Write-Host "  .then(r => r.json())" -ForegroundColor White
        Write-Host "  .then(d => console.log('✓ CORS Working:', d))" -ForegroundColor White
        Write-Host "  .catch(e => console.error('✗ CORS Error:', e));" -ForegroundColor White
        Write-Host ""
        Write-Host "💡 Tip: Open http://localhost:3000 in your browser and run the above in DevTools console" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "📖 For more details, see: CORS_LOCALHOST_SETUP.md" -ForegroundColor Cyan
    } else {
        Write-Host ""
        Write-Host "❌ Terraform apply failed!" -ForegroundColor Red
        Write-Host "   Check the error messages above for details." -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "⏸️  Deployment cancelled. No changes were made." -ForegroundColor Yellow
    Write-Host "   You can review terraform.tfvars and run 'terraform apply' manually when ready." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📝 To revert these changes later:" -ForegroundColor Cyan
Write-Host "   1. Edit terraform.tfvars and remove localhost origins"
Write-Host "   2. Run: terraform apply"
Write-Host ""

# Return to original directory
Set-Location $currentPath

