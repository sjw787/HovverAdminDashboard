# DNS Resolution Issue - api.samwylock.com

## Current Status

✅ **Route53 Record Created**: The Terraform state shows `aws_route53_record.app[0]` was created successfully
✅ **HTTPS Listener Active**: ALB has HTTPS listener on port 443 with ACM certificate
✅ **HTTP Redirect Active**: HTTP requests are being redirected to HTTPS
❌ **DNS Not Resolving Yet**: `api.samwylock.com` is not resolving (ENOTFOUND error)

## Root Cause

The Route53 A record was just created and **DNS propagation takes 5-30 minutes** for the changes to propagate globally.

---

## Immediate Workaround - Use ALB DNS Directly

While waiting for DNS to propagate, you can access your API using the ALB DNS name with HTTPS:

### Option 1: Skip Certificate Verification (Testing Only)

```powershell
# PowerShell
Invoke-WebRequest -Uri "https://hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com/" -SkipCertificateCheck

# Or with curl
curl -k https://hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com/
```

**Note:** The `-k` or `-SkipCertificateCheck` flag is needed because the certificate is for `api.samwylock.com`, not the ALB DNS name.

### Option 2: Test Login via ALB

```powershell
# Test login (skip cert check for testing)
Invoke-WebRequest -Uri "https://hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"sjw787.sw@gmail.com","password":"!%QIwd8d*zS9*aVD"}' `
  -SkipCertificateCheck
```

---

## Verify DNS Propagation

### Check DNS Status

Run these commands every few minutes to check if DNS has propagated:

```powershell
# Check with nslookup
nslookup api.samwylock.com

# Check with PowerShell
Resolve-DnsName api.samwylock.com

# Check with Google DNS specifically
nslookup api.samwylock.com 8.8.8.8
```

**Expected Output (when ready):**
```
Name:    api.samwylock.com
Address: <ALB IP addresses>
Aliases: hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com
```

### Check Route53 Record

Verify the record exists in admin-legacy account:

```powershell
aws route53 list-resource-record-sets `
  --hosted-zone-id Z0463989E6ZRMK2X7OOO `
  --profile admin-legacy `
  --query "ResourceRecordSets[?Name=='api.samwylock.com.']"
```

**Expected Output:**
```json
[
  {
    "Name": "api.samwylock.com.",
    "Type": "A",
    "AliasTarget": {
      "HostedZoneId": "Z35SXDOTRQ7X7K",
      "DNSName": "hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com.",
      "EvaluateTargetHealth": true
    }
  }
]
```

---

## Once DNS Propagates (5-30 minutes)

### Test HTTPS Endpoint

```powershell
# Should work without certificate warnings
Invoke-WebRequest -Uri "https://api.samwylock.com/"

# Expected Response
# {"status":"healthy","app_name":"Hovver Admin Dashboard",...}
```

### Test Login

```powershell
# Login
$response = Invoke-WebRequest -Uri "https://api.samwylock.com/auth/login" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username":"sjw787.sw@gmail.com","password":"!%QIwd8d*zS9*aVD"}'

# Parse response
$tokens = $response.Content | ConvertFrom-Json
Write-Host "Access Token: $($tokens.access_token)"
```

### Update Postman Collection

Update your base URL to:
```
https://api.samwylock.com
```

---

## Troubleshooting

### DNS Still Not Resolving After 30 Minutes

1. **Verify Route53 record exists:**
   ```powershell
   aws route53 list-resource-record-sets --hosted-zone-id Z0463989E6ZRMK2X7OOO --profile admin-legacy
   ```

2. **Check if record is correct:**
   - Name should be: `api.samwylock.com.` (note the trailing dot)
   - Type should be: `A`
   - Alias target should point to ALB DNS name

3. **Flush local DNS cache:**
   ```powershell
   ipconfig /flushdns
   ```

4. **Try different DNS servers:**
   ```powershell
   # Google DNS
   nslookup api.samwylock.com 8.8.8.8
   
   # Cloudflare DNS
   nslookup api.samwylock.com 1.1.1.1
   ```

### Certificate Errors When Using api.samwylock.com

If you get certificate errors when using `api.samwylock.com`, check:

1. **Certificate status:**
   ```powershell
   cd terraform
   terraform state show 'aws_acm_certificate.api[0]'
   ```

2. **Certificate validation:**
   - Check if ACM certificate shows "Issued" status
   - Verify DNS validation records were created

3. **Check certificate ARN in ALB listener:**
   ```powershell
   aws elbv2 describe-listeners --load-balancer-arn $(terraform output -raw alb_arn) --region us-east-1
   ```

---

## Current Configuration

- **Domain**: api.samwylock.com
- **ALB DNS**: hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com
- **HTTPS**: ✅ Enabled (port 443)
- **HTTP Redirect**: ✅ Enabled (port 80 → 443)
- **Certificate**: ACM certificate in primary account
- **DNS Validation**: Via admin-legacy Route53

---

## Summary

**The issue is simply DNS propagation delay.** Everything is configured correctly:

✅ Route53 A record created in admin-legacy  
✅ ACM certificate created and validated  
✅ HTTPS listener configured on ALB  
✅ HTTP redirect enabled  

**You just need to wait 5-30 minutes for DNS to propagate globally.**

### In the meantime:
- Use the ALB DNS name directly with `-k` flag
- Or wait for DNS propagation to complete

### Once DNS works:
- `https://api.samwylock.com/` will work perfectly
- No certificate warnings
- HTTP automatically redirects to HTTPS

---

## Quick Test Commands

```powershell
# Check DNS (run every 5 minutes)
nslookup api.samwylock.com

# Test ALB directly (works now)
Invoke-WebRequest -Uri "https://hovver-admin-alb-2080077084.us-east-1.elb.amazonaws.com/" -SkipCertificateCheck

# Test domain (works after DNS propagates)
Invoke-WebRequest -Uri "https://api.samwylock.com/"
```

**Estimated wait time: 5-15 minutes for DNS propagation**

