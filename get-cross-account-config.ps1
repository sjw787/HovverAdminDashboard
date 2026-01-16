# Script to retrieve ACM Certificate ARN and Route53 Hosted Zone ID from admin-legacy account
# Run this before deploying Terraform to get the necessary values

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Fetching AWS Resources from admin-legacy account" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if admin-legacy profile exists
try {
    $profileCheck = aws configure list --profile admin-legacy 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ AWS profile 'admin-legacy' not found!" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please configure the profile first:" -ForegroundColor Yellow
        Write-Host "  aws configure --profile admin-legacy" -ForegroundColor White
        Write-Host ""
        exit 1
    }
} catch {
    Write-Host "❌ AWS CLI not found or admin-legacy profile not configured" -ForegroundColor Red
    exit 1
}

Write-Host "✅ admin-legacy profile found" -ForegroundColor Green
Write-Host ""

# Get Hosted Zone ID for samwylock.com
Write-Host "Fetching Route53 Hosted Zone for samwylock.com..." -ForegroundColor Cyan
$hostedZoneId = (aws route53 list-hosted-zones-by-name `
    --dns-name samwylock.com `
    --max-items 1 `
    --profile admin-legacy `
    --query "HostedZones[?Name=='samwylock.com.'].Id" `
    --output text)

if ($hostedZoneId) {
    # Remove /hostedzone/ prefix if present
    $hostedZoneId = $hostedZoneId -replace '/hostedzone/', ''
    Write-Host "✅ Found Hosted Zone: $hostedZoneId" -ForegroundColor Green
} else {
    Write-Host "❌ Hosted Zone for samwylock.com not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create a hosted zone in the admin-legacy account first:" -ForegroundColor Yellow
    Write-Host "  aws route53 create-hosted-zone --name samwylock.com --caller-reference $(Get-Date -Format 'yyyyMMddHHmmss') --profile admin-legacy" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""

# Get ACM Certificate ARN for *.samwylock.com or api.samwylock.com
Write-Host "Fetching ACM Certificate for samwylock.com..." -ForegroundColor Cyan
$certArn = (aws acm list-certificates `
    --profile admin-legacy `
    --region us-east-1 `
    --query "CertificateSummaryList[?contains(DomainName, 'samwylock.com')].CertificateArn" `
    --output text)

if ($certArn) {
    # If multiple certificates, take the first one
    $certArn = ($certArn -split "`t")[0]
    Write-Host "✅ Found Certificate: $certArn" -ForegroundColor Green

    # Get certificate details
    Write-Host ""
    Write-Host "Certificate Details:" -ForegroundColor Cyan
    $certDetails = aws acm describe-certificate `
        --certificate-arn $certArn `
        --profile admin-legacy `
        --region us-east-1 `
        --query "Certificate.{Domain:DomainName,Status:Status,SANs:SubjectAlternativeNames}" `
        --output json | ConvertFrom-Json

    Write-Host "  Domain: $($certDetails.Domain)" -ForegroundColor White
    Write-Host "  Status: $($certDetails.Status)" -ForegroundColor $(if ($certDetails.Status -eq "ISSUED") { "Green" } else { "Red" })
    Write-Host "  SANs: $($certDetails.SANs -join ', ')" -ForegroundColor White

    if ($certDetails.Status -ne "ISSUED") {
        Write-Host ""
        Write-Host "⚠️  Warning: Certificate status is not ISSUED" -ForegroundColor Yellow
        Write-Host "   Please ensure the certificate is validated before deploying" -ForegroundColor Yellow
    }
} else {
    Write-Host "❌ No ACM Certificate found for samwylock.com!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please create or import a certificate in the admin-legacy account:" -ForegroundColor Yellow
    Write-Host "  aws acm request-certificate --domain-name api.samwylock.com --subject-alternative-names '*.samwylock.com' --validation-method DNS --profile admin-legacy --region us-east-1" -ForegroundColor White
    Write-Host ""
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Terraform Configuration" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Create or update terraform.tfvars
$tfvarsPath = ".\terraform\terraform.tfvars"

# Check if file exists and has these values already
$needsUpdate = $true
if (Test-Path $tfvarsPath) {
    $existingContent = Get-Content $tfvarsPath -Raw
    if ($existingContent -match "ssl_certificate_arn" -and $existingContent -match "hosted_zone_id") {
        Write-Host "⚠️  terraform.tfvars already contains SSL configuration" -ForegroundColor Yellow
        $overwrite = Read-Host "Do you want to update it? (y/n)"
        if ($overwrite -ne "y") {
            $needsUpdate = $false
        }
    }
}

if ($needsUpdate) {
    $tfvarsContent = @"

# Cross-Account Configuration (admin-legacy)
ssl_certificate_arn   = "$certArn"
hosted_zone_id        = "$hostedZoneId"
domain_name           = "api.samwylock.com"
enable_https_redirect = true

# Update CORS to use HTTPS
cors_origins = ["https://samwylock.com", "https://www.samwylock.com"]
"@

    if (!(Test-Path $tfvarsPath)) {
        # Create new file
        $tfvarsContent | Out-File -FilePath $tfvarsPath -Encoding UTF8
        Write-Host "✅ Created terraform.tfvars with configuration" -ForegroundColor Green
    } else {
        # Append to existing file
        $tfvarsContent | Out-File -FilePath $tfvarsPath -Append -Encoding UTF8
        Write-Host "✅ Updated terraform.tfvars with configuration" -ForegroundColor Green
    }

    Write-Host ""
    Write-Host "Configuration written to: terraform\terraform.tfvars" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Hosted Zone ID:    $hostedZoneId" -ForegroundColor White
Write-Host "Certificate ARN:   $certArn" -ForegroundColor White
Write-Host "Domain:            api.samwylock.com" -ForegroundColor White
Write-Host "HTTPS Redirect:    Enabled" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Next Steps" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Review the configuration:" -ForegroundColor Yellow
Write-Host "   cat terraform\terraform.tfvars" -ForegroundColor White
Write-Host ""
Write-Host "2. Deploy the infrastructure:" -ForegroundColor Yellow
Write-Host "   cd terraform" -ForegroundColor White
Write-Host "   terraform plan" -ForegroundColor White
Write-Host "   terraform apply" -ForegroundColor White
Write-Host ""
Write-Host "3. After deployment, your API will be available at:" -ForegroundColor Yellow
Write-Host "   https://api.samwylock.com" -ForegroundColor Green
Write-Host ""

Write-Host "⚠️  Important: Make sure the admin-legacy AWS profile has permissions to:" -ForegroundColor Yellow
Write-Host "   - Read ACM certificates" -ForegroundColor White
Write-Host "   - Create/update Route53 records" -ForegroundColor White
Write-Host ""

