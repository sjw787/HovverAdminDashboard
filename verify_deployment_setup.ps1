#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Verify deployment mode setup and show current configuration

.DESCRIPTION
    This script checks your Terraform configuration and shows which deployment
    mode is currently configured. It also validates that all required files exist.

.PARAMETER ShowDetails
    Show detailed information about both deployment modes

.EXAMPLE
    .\verify_deployment_setup.ps1

.EXAMPLE
    .\verify_deployment_setup.ps1 -ShowDetails
#>

param(
    [switch]$ShowDetails
)

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Deployment Mode Verification" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if terraform directory exists
if (-not (Test-Path "terraform")) {
    Write-Host "❌ Error: terraform directory not found" -ForegroundColor Red
    Write-Host "   Make sure you're running this from the project root" -ForegroundColor Yellow
    exit 1
}

# Check terraform.tfvars
$tfvarsPath = "terraform/terraform.tfvars"
if (-not (Test-Path $tfvarsPath)) {
    Write-Host "⚠️  Warning: terraform.tfvars not found" -ForegroundColor Yellow
    Write-Host "   Copy terraform.tfvars.example to terraform.tfvars" -ForegroundColor Yellow
    Write-Host "   Command: Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars`n" -ForegroundColor Gray
    $mode = "NOT CONFIGURED"
} else {
    # Read deployment mode from tfvars
    $tfvarsContent = Get-Content $tfvarsPath -Raw
    if ($tfvarsContent -match 'deployment_mode\s*=\s*"(\w+)"') {
        $mode = $matches[1]
    } else {
        $mode = "NOT SET (defaults to 'ecs')"
    }
}

Write-Host "Current Deployment Mode: " -NoNewline
if ($mode -eq "ecs") {
    Write-Host "ECS" -ForegroundColor Green
} elseif ($mode -eq "lambda") {
    Write-Host "LAMBDA" -ForegroundColor Green
} else {
    Write-Host $mode -ForegroundColor Yellow
}

# Check required files
Write-Host "`nRequired Files Check:" -ForegroundColor Cyan

$files = @{
    "Dockerfile" = "ECS container image"
    "Dockerfile.lambda" = "Lambda container image"
    "lambda_handler.py" = "Lambda entry point"
    "build_and_push_docker.ps1" = "Build and deploy script"
    "terraform/lambda.tf" = "Lambda infrastructure"
    "terraform/ecs.tf" = "ECS infrastructure"
    "terraform/variables.tf" = "Terraform variables"
    "pyproject.toml" = "Python dependencies"
}

$allFilesExist = $true
foreach ($file in $files.Keys) {
    if (Test-Path $file) {
        Write-Host "  ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "  ❌ $file - MISSING" -ForegroundColor Red
        $allFilesExist = $false
    }
}

# Check if mangum is in pyproject.toml
if (Test-Path "pyproject.toml") {
    $pyprojectContent = Get-Content "pyproject.toml" -Raw
    if ($pyprojectContent -match 'mangum') {
        Write-Host "  ✅ mangum dependency (for Lambda)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  mangum not found in pyproject.toml" -ForegroundColor Yellow
        Write-Host "     Lambda deployment requires mangum" -ForegroundColor Yellow
    }
}

Write-Host ""

# Show deployment mode details if requested
if ($ShowDetails) {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Deployment Mode Comparison" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan

    Write-Host "ECS FARGATE MODE" -ForegroundColor Green
    Write-Host "  Best for: Production with steady traffic"
    Write-Host "  Pros: No cold starts, consistent performance, predictable costs"
    Write-Host "  Cons: Always-on (higher minimum cost)"
    Write-Host "  Cost: ~`$15-20/month base"
    Write-Host "  Dockerfile: Dockerfile"
    Write-Host ""

    Write-Host "LAMBDA MODE" -ForegroundColor Green
    Write-Host "  Best for: Development, testing, variable workloads"
    Write-Host "  Pros: Pay per use, auto-scales to zero, serverless"
    Write-Host "  Cons: Cold starts, 15min max execution time"
    Write-Host "  Cost: `$0 when idle, ~`$1-10/month for low-medium traffic"
    Write-Host "  Dockerfile: Dockerfile.lambda"
    Write-Host ""
}

# Show next steps
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if ($mode -eq "NOT CONFIGURED") {
    Write-Host "1. Create terraform.tfvars from example:"
    Write-Host "   Copy-Item terraform/terraform.tfvars.example terraform/terraform.tfvars`n" -ForegroundColor Gray
    Write-Host "2. Edit terraform/terraform.tfvars and set deployment_mode = `"ecs`" or `"lambda`"`n"
    Write-Host "3. Deploy infrastructure:"
    Write-Host "   cd terraform; terraform apply`n" -ForegroundColor Gray
    Write-Host "4. Build and deploy application:"
    Write-Host "   .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode ecs`n" -ForegroundColor Gray
} elseif ($mode -eq "ecs") {
    Write-Host "To deploy to ECS:"
    Write-Host "  cd terraform; terraform apply" -ForegroundColor Gray
    Write-Host "  cd ..; .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode ecs`n" -ForegroundColor Gray
    Write-Host "To switch to Lambda:"
    Write-Host "  1. Edit terraform/terraform.tfvars: deployment_mode = `"lambda`""
    Write-Host "  2. cd terraform; terraform apply" -ForegroundColor Gray
    Write-Host "  3. cd ..; .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode lambda`n" -ForegroundColor Gray
} elseif ($mode -eq "lambda") {
    Write-Host "To deploy to Lambda:"
    Write-Host "  cd terraform; terraform apply" -ForegroundColor Gray
    Write-Host "  cd ..; .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode lambda`n" -ForegroundColor Gray
    Write-Host "To switch to ECS:"
    Write-Host "  1. Edit terraform/terraform.tfvars: deployment_mode = `"ecs`""
    Write-Host "  2. cd terraform; terraform apply" -ForegroundColor Gray
    Write-Host "  3. cd ..; .\build_and_push_docker.ps1 -Profile your-aws-profile -Mode ecs`n" -ForegroundColor Gray
}

Write-Host "`nDocumentation:" -ForegroundColor Cyan
Write-Host "  DEPLOYMENT_MODES.md - Comprehensive deployment guide"
Write-Host "  QUICK_DEPLOY.md     - Quick reference commands"
Write-Host "  README.md           - Full project documentation`n"

if ($allFilesExist) {
    Write-Host "✅ Setup verification complete!`n" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some files are missing. Setup may be incomplete.`n" -ForegroundColor Yellow
}
