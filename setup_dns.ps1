# DNS Setup Script for AWS SES
# This script helps you set up DNS records for SES email verification
#
# Usage:
#   .\setup_dns.ps1 -Domain "samwylock.com" -Provider "cloudflare"
#   .\setup_dns.ps1 -Domain "samwylock.com" -Provider "route53"
#   .\setup_dns.ps1 -ShowInstructions

param(
    [string]$Domain = "",
    [string]$Provider = "",
    [string]$VerificationToken = "",
    [string[]]$DkimTokens = @(),
    [switch]$ShowInstructions = $false,
    [switch]$Route53 = $false,
    [switch]$DryRun = $false
)

# Colors for output
$Green = "Green"
$Yellow = "Yellow"
$Red = "Red"
$Cyan = "Cyan"

function Show-Banner {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "         AWS SES DNS Setup Script                              " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Show-Instructions {
    Write-Host "DNS Setup Instructions" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "This script helps you set up DNS records for AWS SES." -ForegroundColor White
    Write-Host ""
    Write-Host "STEP 1: Get DNS records from SES" -ForegroundColor Yellow
    Write-Host "  python setup_ses.py --domain samwylock.com" -ForegroundColor Gray
    Write-Host ""
    Write-Host "STEP 2: Run this script with the tokens" -ForegroundColor Yellow
    Write-Host "  .\setup_dns.ps1 -Domain 'samwylock.com' -Provider 'cloudflare'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Supported Providers:" -ForegroundColor Yellow
    Write-Host "  - route53     - AWS Route 53" -ForegroundColor Gray
    Write-Host "  - cloudflare  - Cloudflare (requires API token)" -ForegroundColor Gray
    Write-Host "  - manual      - Show records to add manually" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or use Route53 directly:" -ForegroundColor Yellow
    Write-Host "  .\setup_dns.ps1 -Domain 'samwylock.com' -Route53" -ForegroundColor Gray
    Write-Host ""
}

function Get-SESRecords {
    param([string]$Domain)

    Write-Host "[FETCH] Fetching SES DNS records from AWS..." -ForegroundColor Cyan
    Write-Host ""

    try {
        # Get verification token
        $verifyResult = aws ses verify-domain-identity --domain $Domain --region us-east-1 --output json | ConvertFrom-Json
        $verificationToken = $verifyResult.VerificationToken

        # Get DKIM tokens
        $dkimResult = aws ses verify-domain-dkim --domain $Domain --region us-east-1 --output json | ConvertFrom-Json
        $dkimTokens = $dkimResult.DkimTokens

        return @{
            VerificationToken = $verificationToken
            DkimTokens = $dkimTokens
            Success = $true
        }
    }
    catch {
        Write-Host "[ERROR] Error fetching SES records: $_" -ForegroundColor Red
        return @{ Success = $false }
    }
}

function Show-ManualInstructions {
    param(
        [string]$Domain,
        [string]$VerificationToken,
        [string[]]$DkimTokens
    )

    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "         DNS RECORDS TO ADD MANUALLY                            " -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "Domain: $Domain" -ForegroundColor Yellow
    Write-Host ""

    # Verification record
    Write-Host "1. DOMAIN VERIFICATION (Required)" -ForegroundColor Green
    Write-Host "   ------------------------------------------------" -ForegroundColor Gray
    Write-Host "   Type:  TXT" -ForegroundColor White
    Write-Host "   Name:  _amazonses.$Domain" -ForegroundColor White
    Write-Host "   Value: $VerificationToken" -ForegroundColor Yellow
    Write-Host "   TTL:   300" -ForegroundColor White
    Write-Host ""

    # DKIM records
    Write-Host "2. DKIM RECORDS (Required - Add all 3)" -ForegroundColor Green
    Write-Host "   ------------------------------------------------" -ForegroundColor Gray

    for ($i = 0; $i -lt $DkimTokens.Count; $i++) {
        $token = $DkimTokens[$i]
        Write-Host ""
        Write-Host "   Record $($i + 1):" -ForegroundColor Cyan
        Write-Host "   Type:  CNAME" -ForegroundColor White
        Write-Host ("   Name:  " + $token + "._domainkey." + $Domain) -ForegroundColor White
        Write-Host ("   Value: " + $token + ".dkim.amazonses.com") -ForegroundColor Yellow
        Write-Host "   TTL:   300" -ForegroundColor White
    }

    # SPF record
    Write-Host ""
    Write-Host "3. SPF RECORD (Recommended)" -ForegroundColor Green
    Write-Host "   ------------------------------------------------" -ForegroundColor Gray
    Write-Host "   Type:  TXT" -ForegroundColor White
    Write-Host "   Name:  $Domain" -ForegroundColor White
    Write-Host "   Value: v=spf1 include:amazonses.com ~all" -ForegroundColor Yellow
    Write-Host "   TTL:   300" -ForegroundColor White
    Write-Host ""

    # DMARC record
    Write-Host "4. DMARC RECORD (Recommended)" -ForegroundColor Green
    Write-Host "   ------------------------------------------------" -ForegroundColor Gray
    Write-Host "   Type:  TXT" -ForegroundColor White
    Write-Host "   Name:  _dmarc.$Domain" -ForegroundColor White
    Write-Host "   Value: v=DMARC1; p=none; rua=mailto:postmaster@$Domain" -ForegroundColor Yellow
    Write-Host "   TTL:   300" -ForegroundColor White
    Write-Host ""

    Write-Host "NOTES:" -ForegroundColor Cyan
    Write-Host "   - Add these records to your DNS provider" -ForegroundColor White
    Write-Host "   - Verification takes 5-30 minutes (up to 72 hours)" -ForegroundColor White
    Write-Host "   - Check status: python setup_ses.py --check-status $Domain" -ForegroundColor White
    Write-Host ""
}

function Add-Route53Records {
    param(
        [string]$Domain,
        [string]$VerificationToken,
        [string[]]$DkimTokens,
        [bool]$DryRun = $false
    )

    Write-Host "[Route53] Setting up DNS records..." -ForegroundColor Cyan
    Write-Host ""

    # Check if admin-legacy profile exists
    Write-Host "   Checking for admin-legacy AWS profile..." -ForegroundColor Gray
    try {
        $profileCheck = aws configure list --profile admin-legacy 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "   [ERROR] AWS profile 'admin-legacy' not found!" -ForegroundColor Red
            Write-Host "   Please configure the profile first:" -ForegroundColor Yellow
            Write-Host "     aws configure --profile admin-legacy" -ForegroundColor White
            Write-Host ""
            return
        }
        Write-Host "   [OK] Found admin-legacy profile" -ForegroundColor Green
    }
    catch {
        Write-Host "   [ERROR] Failed to check AWS profile: $_" -ForegroundColor Red
        return
    }

    # Get hosted zone ID from admin-legacy account
    Write-Host "   Finding hosted zone for $Domain in admin-legacy account..." -ForegroundColor Gray
    $hostedZones = aws route53 list-hosted-zones --profile admin-legacy --output json | ConvertFrom-Json
    $zone = $hostedZones.HostedZones | Where-Object { $_.Name -eq "$Domain." }

    if (-not $zone) {
        Write-Host "[ERROR] Hosted zone not found for $Domain" -ForegroundColor Red
        Write-Host "   Please create a hosted zone first in Route 53" -ForegroundColor Yellow
        return
    }

    $zoneId = $zone.Id
    Write-Host "   [OK] Found hosted zone: $zoneId" -ForegroundColor Green
    Write-Host ""

    $dryRunText = if ($DryRun) { " (DRY RUN)" } else { "" }

    # Create change batch JSON
    $changes = @()

    # 1. Verification record
    Write-Host "   [+] Adding verification TXT record$dryRunText..." -ForegroundColor Cyan
    $changes += @{
        Action = "UPSERT"
        ResourceRecordSet = @{
            Name = "_amazonses.$Domain"
            Type = "TXT"
            TTL = 300
            ResourceRecords = @(@{ Value = "`"$VerificationToken`"" })
        }
    }

    # 2. DKIM records
    foreach ($token in $DkimTokens) {
        Write-Host "   [+] Adding DKIM CNAME record for $token$dryRunText..." -ForegroundColor Cyan
        $changes += @{
            Action = "UPSERT"
            ResourceRecordSet = @{
                Name = "$token._domainkey.$Domain"
                Type = "CNAME"
                TTL = 300
                ResourceRecords = @(@{ Value = "$token.dkim.amazonses.com" })
            }
        }
    }

    # 3. SPF record
    Write-Host "   [+] Adding SPF TXT record$dryRunText..." -ForegroundColor Cyan
    $changes += @{
        Action = "UPSERT"
        ResourceRecordSet = @{
            Name = $Domain
            Type = "TXT"
            TTL = 300
            ResourceRecords = @(@{ Value = "`"v=spf1 include:amazonses.com ~all`"" })
        }
    }

    # 4. DMARC record
    Write-Host "   [+] Adding DMARC TXT record$dryRunText..." -ForegroundColor Cyan
    $changes += @{
        Action = "UPSERT"
        ResourceRecordSet = @{
            Name = "_dmarc.$Domain"
            Type = "TXT"
            TTL = 300
            ResourceRecords = @(@{ Value = "`"v=DMARC1; p=none; rua=mailto:postmaster@$Domain`"" })
        }
    }

    if (-not $DryRun) {
        # Create change batch
        $changeBatch = @{
            Comment = "SES email verification records"
            Changes = $changes
        }

        # Convert to JSON with proper formatting for AWS CLI
        $jsonBatch = $changeBatch | ConvertTo-Json -Depth 10 -Compress

        # Save to temp file with UTF8 encoding without BOM
        $tempFile = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($tempFile, $jsonBatch, [System.Text.UTF8Encoding]::new($false))

        try {
            # Apply changes
            Write-Host ""
            Write-Host "   [APPLY] Applying DNS changes to admin-legacy account..." -ForegroundColor Yellow

            $result = aws route53 change-resource-record-sets `
                --hosted-zone-id $zoneId `
                --change-batch "file://$tempFile" `
                --profile admin-legacy `
                --output json 2>&1

            if ($LASTEXITCODE -eq 0) {
                $resultObj = $result | ConvertFrom-Json
                Write-Host ""
                Write-Host "   [OK] DNS records added successfully!" -ForegroundColor Green
                Write-Host "   Change ID: $($resultObj.ChangeInfo.Id)" -ForegroundColor Gray
                Write-Host "   Status: $($resultObj.ChangeInfo.Status)" -ForegroundColor Gray
                Write-Host ""
                Write-Host "   [WAIT] DNS propagation may take 5-30 minutes" -ForegroundColor Yellow
                Write-Host "   Check status: python setup_ses.py --check-status $Domain" -ForegroundColor White
                Write-Host ""
            } else {
                Write-Host ""
                Write-Host "   [ERROR] Error adding DNS records:" -ForegroundColor Red
                Write-Host $result -ForegroundColor Red
            }
        }
        catch {
            Write-Host ""
            Write-Host "   [ERROR] Error adding DNS records: $_" -ForegroundColor Red
        }
        finally {
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        }
    }
    else {
        Write-Host ""
        Write-Host "   [INFO] DRY RUN - No changes were made" -ForegroundColor Yellow
        Write-Host "   Remove -DryRun flag to apply changes" -ForegroundColor White
        Write-Host ""
    }
}

# Main script logic
Show-Banner

if ($ShowInstructions) {
    Show-Instructions
    exit 0
}

if (-not $Domain) {
    Write-Host "[ERROR] Domain parameter is required" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\setup_dns.ps1 -Domain 'samwylock.com' -Route53" -ForegroundColor White
    Write-Host "  .\setup_dns.ps1 -ShowInstructions" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Fetch SES records if not provided
if (-not $VerificationToken -or $DkimTokens.Count -eq 0) {
    $sesRecords = Get-SESRecords -Domain $Domain

    if (-not $sesRecords.Success) {
        Write-Host "[ERROR] Failed to fetch SES records" -ForegroundColor Red
        exit 1
    }

    $VerificationToken = $sesRecords.VerificationToken
    $DkimTokens = $sesRecords.DkimTokens

    Write-Host "[OK] Fetched SES records successfully" -ForegroundColor Green
    Write-Host ""
}

# Process based on provider
if ($Route53 -or $Provider -eq "route53") {
    Add-Route53Records -Domain $Domain -VerificationToken $VerificationToken -DkimTokens $DkimTokens -DryRun:$DryRun
}
elseif ($Provider -eq "manual" -or $Provider -eq "") {
    Show-ManualInstructions -Domain $Domain -VerificationToken $VerificationToken -DkimTokens $DkimTokens
}
else {
    Write-Host "[ERROR] Unsupported provider: $Provider" -ForegroundColor Red
    Write-Host ""
    Write-Host "Supported providers:" -ForegroundColor Yellow
    Write-Host "  * route53" -ForegroundColor White
    Write-Host "  * manual" -ForegroundColor White
    Write-Host ""
    exit 1
}
