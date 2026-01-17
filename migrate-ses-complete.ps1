# Complete SES Account Migration Script
# This script automates the entire migration process

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  SES Account Migration: iamadmin-general -> iamadmin-dev" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$targetAccount = "052869941234"
$wrongAccount = "777653593792"

# Step 1: Check current account
Write-Host "[STEP 1] Checking current AWS account..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    $currentAccount = $identity.Account
    Write-Host "  Current Account: $currentAccount" -ForegroundColor White

    if ($currentAccount -eq $targetAccount) {
        Write-Host "  [OK] Already in target account (iamadmin-dev)!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Setting up SES in this account..." -ForegroundColor Yellow
        python migrate_ses_account.py --setup-only
        Write-Host ""
        Write-Host "[SUCCESS] SES has been configured in iamadmin-dev!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Yellow
        Write-Host "1. Wait 5-30 minutes for DNS propagation" -ForegroundColor White
        Write-Host "2. Check status: python setup_ses.py --check-status samwylock.com" -ForegroundColor White
        Write-Host "3. Configure Cognito to use SES" -ForegroundColor White
        exit 0
    }
    elseif ($currentAccount -eq $wrongAccount) {
        Write-Host "  [INFO] In iamadmin-general (wrong account)" -ForegroundColor Yellow
        Write-Host ""

        # Step 2: Delete from wrong account
        Write-Host "[STEP 2] Deleting SES from iamadmin-general..." -ForegroundColor Yellow
        Write-Host "  This will remove samwylock.com from SES in account $wrongAccount" -ForegroundColor White
        Write-Host ""

        $confirm = Read-Host "  Delete SES domain from current account? (yes/no)"
        if ($confirm -ne "yes") {
            Write-Host "[CANCELLED] No changes made" -ForegroundColor Red
            exit 1
        }

        python migrate_ses_account.py
        Write-Host ""
        Write-Host "  [OK] SES deleted from iamadmin-general" -ForegroundColor Green
    }
    else {
        Write-Host "  [WARNING] In unexpected account: $currentAccount" -ForegroundColor Red
        Write-Host "  Expected either $wrongAccount or $targetAccount" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  [ERROR] Could not check AWS account: $_" -ForegroundColor Red
    exit 1
}

# Step 3: Instructions to switch accounts
Write-Host ""
Write-Host "[STEP 3] Switch to iamadmin-dev account" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "You need to switch AWS credentials to account $targetAccount" -ForegroundColor White
Write-Host ""

# Check if iamadmin-dev profile exists
$credFile = Join-Path $env:USERPROFILE ".aws\credentials"
$hasDevProfile = $false

if (Test-Path $credFile) {
    $profiles = Get-Content $credFile | Select-String -Pattern "^\[(.+)\]" | ForEach-Object { $_.Matches.Groups[1].Value }
    if ($profiles -contains "iamadmin-dev") {
        $hasDevProfile = $true
    }
}

if ($hasDevProfile) {
    Write-Host "Found iamadmin-dev profile. To switch, run:" -ForegroundColor Green
    Write-Host ""
    Write-Host '  $env:AWS_PROFILE="iamadmin-dev"' -ForegroundColor Cyan
    Write-Host '  Remove-Item Env:AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue' -ForegroundColor Cyan
    Write-Host '  Remove-Item Env:AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue' -ForegroundColor Cyan
    Write-Host '  Remove-Item Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue' -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Then run this script again:" -ForegroundColor Yellow
    Write-Host "  .\migrate-ses-complete.ps1" -ForegroundColor Cyan
}
else {
    Write-Host "iamadmin-dev profile not found. You have two options:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Configure iamadmin-dev profile" -ForegroundColor Green
    Write-Host "  aws configure --profile iamadmin-dev" -ForegroundColor Cyan
    Write-Host "  # Enter access key and secret for account $targetAccount" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Use environment variables" -ForegroundColor Green
    Write-Host '  $env:AWS_ACCESS_KEY_ID="<your-key-for-052869941234>"' -ForegroundColor Cyan
    Write-Host '  $env:AWS_SECRET_ACCESS_KEY="<your-secret-for-052869941234>"' -ForegroundColor Cyan
    Write-Host '  Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue' -ForegroundColor Cyan
    Write-Host ""
    Write-Host "After setting credentials, run this script again:" -ForegroundColor Yellow
    Write-Host "  .\migrate-ses-complete.ps1" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
