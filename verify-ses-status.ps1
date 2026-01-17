# Quick SES Verification Status Check
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SES Domain Verification Status" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Domain: samwylock.com" -ForegroundColor Yellow
Write-Host ""

# Check domain verification
Write-Host "1. Domain Verification Status:" -ForegroundColor Cyan
$verifyStatus = aws ses get-identity-verification-attributes --identities samwylock.com --region us-east-1 --output json | ConvertFrom-Json
$domainStatus = $verifyStatus.VerificationAttributes.'samwylock.com'.VerificationStatus
Write-Host "   Status: $domainStatus" -ForegroundColor $(if ($domainStatus -eq "Success") { "Green" } else { "Yellow" })
Write-Host ""

# Check DKIM status
Write-Host "2. DKIM Status:" -ForegroundColor Cyan
$dkimStatus = aws ses get-identity-dkim-attributes --identities samwylock.com --region us-east-1 --output json | ConvertFrom-Json
$dkimEnabled = $dkimStatus.DkimAttributes.'samwylock.com'.DkimEnabled
$dkimVerification = $dkimStatus.DkimAttributes.'samwylock.com'.DkimVerificationStatus
$dkimTokens = $dkimStatus.DkimAttributes.'samwylock.com'.DkimTokens

Write-Host "   Enabled: $dkimEnabled" -ForegroundColor $(if ($dkimEnabled) { "Green" } else { "Red" })
Write-Host "   Verification: $dkimVerification" -ForegroundColor $(if ($dkimVerification -eq "Success") { "Green" } else { "Yellow" })
Write-Host "   Tokens:" -ForegroundColor White
foreach ($token in $dkimTokens) {
    Write-Host "     - $token" -ForegroundColor Gray
}
Write-Host ""

# Check DNS records in Route53
Write-Host "3. DNS Records in Route53 (admin-legacy):" -ForegroundColor Cyan
$dnsRecords = aws route53 list-resource-record-sets --hosted-zone-id Z0463989E6ZRMK2X7OOO --profile admin-legacy --query "ResourceRecordSets[?contains(Name, '_domainkey') || contains(Name, 'amazonses') || contains(Name, '_dmarc')]" --output json | ConvertFrom-Json

Write-Host "   Found $($dnsRecords.Count) SES-related records:" -ForegroundColor White
foreach ($record in $dnsRecords) {
    Write-Host "     - $($record.Type): $($record.Name)" -ForegroundColor Gray
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
if ($domainStatus -eq "Success" -and $dkimVerification -eq "Success") {
    Write-Host "[OK] Domain is fully verified and ready for sending emails!" -ForegroundColor Green
} elseif ($domainStatus -eq "Success") {
    Write-Host "[WAIT] Domain is verified, but DKIM verification is pending" -ForegroundColor Yellow
} else {
    Write-Host "[WAIT] Domain verification is pending" -ForegroundColor Yellow
}
Write-Host ""
