# Check AWS Profile Configuration and Switch to iamadmin-dev
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "AWS Account Diagnostic Tool" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Check current environment
Write-Host "Current Environment:" -ForegroundColor Yellow
Write-Host "  AWS_PROFILE: $env:AWS_PROFILE"
Write-Host "  AWS_ACCESS_KEY_ID: $(if ($env:AWS_ACCESS_KEY_ID) { '***' + $env:AWS_ACCESS_KEY_ID.Substring([Math]::Max(0,$env:AWS_ACCESS_KEY_ID.Length-4)) } else { '(not set)' })"
Write-Host "  AWS_SECRET_ACCESS_KEY: $(if ($env:AWS_SECRET_ACCESS_KEY) { '(set)' } else { '(not set)' })"
Write-Host ""

# Check available profiles
Write-Host "Available AWS Profiles:" -ForegroundColor Yellow
$credFile = Join-Path $env:USERPROFILE ".aws\credentials"
if (Test-Path $credFile) {
    $profiles = Get-Content $credFile | Select-String -Pattern "^\[(.+)\]" | ForEach-Object { $_.Matches.Groups[1].Value }
    if ($profiles) {
        foreach ($profile in $profiles) {
            Write-Host "  - $profile" -ForegroundColor White
        }
    } else {
        Write-Host "  No profiles found" -ForegroundColor Red
    }
} else {
    Write-Host "  Credentials file not found: $credFile" -ForegroundColor Red
}
Write-Host ""

# Check current account
Write-Host "Checking current AWS account..." -ForegroundColor Yellow
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "  Account ID: $($identity.Account)" -ForegroundColor $(if ($identity.Account -eq "052869941234") { "Green" } else { "Red" })
    Write-Host "  User ARN: $($identity.Arn)" -ForegroundColor White
    Write-Host ""

    if ($identity.Account -eq "052869941234") {
        Write-Host "[OK] You are in the correct account (iamadmin-dev)!" -ForegroundColor Green
        Write-Host ""
        Write-Host "You can now run:" -ForegroundColor Yellow
        Write-Host "  python migrate_ses_account.py --setup-only" -ForegroundColor White
    } elseif ($identity.Account -eq "777653593792") {
        Write-Host "[WARNING] You are in iamadmin-general account" -ForegroundColor Red
        Write-Host "          SES should not be configured here!" -ForegroundColor Red
        Write-Host ""
        Write-Host "First, delete SES from this account:" -ForegroundColor Yellow
        Write-Host "  python migrate_ses_account.py" -ForegroundColor White
        Write-Host ""
        Write-Host "Then switch to iamadmin-dev account (see below)" -ForegroundColor Yellow
    } else {
        Write-Host "[INFO] You are in account: $($identity.Account)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  [ERROR] Could not determine current account: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "How to Switch to iamadmin-dev Account" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Option 1: Use AWS Profile (Recommended)" -ForegroundColor Yellow
Write-Host "  If you have iamadmin-dev profile configured:" -ForegroundColor White
Write-Host '    $env:AWS_PROFILE="iamadmin-dev"' -ForegroundColor Gray
Write-Host '    Remove-Item Env:AWS_ACCESS_KEY_ID -ErrorAction SilentlyContinue' -ForegroundColor Gray
Write-Host '    Remove-Item Env:AWS_SECRET_ACCESS_KEY -ErrorAction SilentlyContinue' -ForegroundColor Gray
Write-Host '    Remove-Item Env:AWS_SESSION_TOKEN -ErrorAction SilentlyContinue' -ForegroundColor Gray
Write-Host ""

Write-Host "Option 2: Configure New Profile" -ForegroundColor Yellow
Write-Host "  If you don't have iamadmin-dev profile:" -ForegroundColor White
Write-Host '    aws configure --profile iamadmin-dev' -ForegroundColor Gray
Write-Host "  Then enter the access key and secret for account 052869941234" -ForegroundColor White
Write-Host ""

Write-Host "Option 3: Use Environment Variables" -ForegroundColor Yellow
Write-Host "  Set credentials directly (less secure):" -ForegroundColor White
Write-Host '    $env:AWS_ACCESS_KEY_ID="<your-access-key-for-052869941234>"' -ForegroundColor Gray
Write-Host '    $env:AWS_SECRET_ACCESS_KEY="<your-secret-key-for-052869941234>"' -ForegroundColor Gray
Write-Host '    Remove-Item Env:AWS_PROFILE -ErrorAction SilentlyContinue' -ForegroundColor Gray
Write-Host ""

Write-Host "After switching, verify with:" -ForegroundColor Yellow
Write-Host "  .\check-aws-account.ps1" -ForegroundColor White
Write-Host ""
