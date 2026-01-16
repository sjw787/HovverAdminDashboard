# Cross-Account HTTPS Setup Guide
## Using Existing ACM Certificate and Route53 from admin-legacy Account

This guide explains how to configure your Hovver Admin Dashboard to use:
- **Domain**: api.samwylock.com
- **ACM Certificate**: From admin-legacy account
- **Route53 Hosted Zone**: samwylock.com from admin-legacy account

---

## Overview

Your setup uses **two AWS accounts**:
1. **Primary Account** (current) - Where ECS, ALB, VPC, and other resources live
2. **admin-legacy Account** - Where ACM certificate and Route53 hosted zone exist

Terraform will:
- Create ALB and infrastructure in the primary account
- Use ACM certificate from admin-legacy account
- Create Route53 DNS record in admin-legacy account pointing to the ALB

---

## Prerequisites

✅ AWS CLI configured with `admin-legacy` profile  
✅ ACM certificate in admin-legacy account (us-east-1 region)  
✅ Route53 hosted zone for samwylock.com in admin-legacy account  
✅ Permissions to read ACM certificates in admin-legacy  
✅ Permissions to create Route53 records in admin-legacy  

---

## Quick Setup

### Step 1: Configure admin-legacy Profile

If you haven't already configured the profile:

```powershell
aws configure --profile admin-legacy
```

Enter your access key, secret key, and region (us-east-1).

### Step 2: Fetch Configuration

Run the helper script to automatically fetch certificate ARN and hosted zone ID:

```powershell
.\get-cross-account-config.ps1
```

This script will:
- ✅ Verify admin-legacy profile exists
- ✅ Fetch Route53 hosted zone ID for samwylock.com
- ✅ Fetch ACM certificate ARN for samwylock.com
- ✅ Create/update terraform.tfvars with the values
- ✅ Show you the configuration summary

### Step 3: Review Configuration

Check the generated terraform.tfvars:

```powershell
cat terraform\terraform.tfvars
```

Should contain:
```hcl
ssl_certificate_arn   = "arn:aws:acm:us-east-1:123456789012:certificate/abc-123..."
hosted_zone_id        = "Z1234567890ABC"
domain_name           = "api.samwylock.com"
enable_https_redirect = true
cors_origins          = ["https://samwylock.com", "https://www.samwylock.com"]
```

### Step 4: Deploy

```powershell
cd terraform
terraform init
terraform plan
terraform apply
```

**Expected changes:**
- ✅ Create HTTPS listener on ALB (with certificate from admin-legacy)
- ✅ Create HTTP listener with redirect to HTTPS
- ✅ Create Route53 A record in admin-legacy pointing to ALB
- ✅ Update ECS task definitions with HTTPS CORS origins

### Step 5: Verify

After deployment (5-10 minutes):

```powershell
# Test DNS resolution
nslookup api.samwylock.com

# Test HTTPS endpoint
curl https://api.samwylock.com/

# Test HTTP redirect
curl -I http://api.samwylock.com/
# Should return: HTTP 301 -> https://api.samwylock.com/
```

---

## Manual Setup (Alternative)

If you prefer to configure manually without the script:

### 1. Get Hosted Zone ID

```powershell
aws route53 list-hosted-zones-by-name `
  --dns-name samwylock.com `
  --profile admin-legacy `
  --query "HostedZones[?Name=='samwylock.com.'].Id" `
  --output text
```

Copy the ID (remove `/hostedzone/` prefix if present).

### 2. Get Certificate ARN

```powershell
aws acm list-certificates `
  --profile admin-legacy `
  --region us-east-1 `
  --query "CertificateSummaryList[?contains(DomainName, 'samwylock.com')].CertificateArn" `
  --output text
```

### 3. Verify Certificate Status

```powershell
aws acm describe-certificate `
  --certificate-arn YOUR_CERT_ARN `
  --profile admin-legacy `
  --region us-east-1 `
  --query "Certificate.Status" `
  --output text
```

Should return: `ISSUED`

### 4. Create terraform.tfvars

Create `terraform/terraform.tfvars`:

```hcl
# Cross-Account Configuration
ssl_certificate_arn   = "arn:aws:acm:us-east-1:YOUR_ACCOUNT:certificate/YOUR_CERT_ID"
hosted_zone_id        = "YOUR_HOSTED_ZONE_ID"
domain_name           = "api.samwylock.com"
enable_https_redirect = true

# CORS Configuration
cors_origins = ["https://samwylock.com", "https://www.samwylock.com"]
```

### 5. Deploy

```powershell
cd terraform
terraform apply
```

---

## How It Works

### Terraform Provider Configuration

The setup uses two AWS providers:

```hcl
# Primary account (current)
provider "aws" {
  region = "us-east-1"
}

# admin-legacy account (for ACM and Route53)
provider "aws" {
  alias   = "admin_legacy"
  region  = "us-east-1"
  profile = "admin-legacy"
}
```

### Resource Creation

**In Primary Account:**
- ALB with HTTPS listener using certificate ARN from admin-legacy
- ECS tasks, VPC, security groups, etc.

**In admin-legacy Account:**
- Route53 A record: api.samwylock.com → ALB DNS name

### Cross-Account Certificate Usage

ALB can use ACM certificates from other accounts **as long as**:
- ✅ Certificate is in the same region (us-east-1)
- ✅ You have the certificate ARN
- ✅ Certificate status is ISSUED

No additional IAM permissions needed for ALB to use the certificate!

---

## Troubleshooting

### admin-legacy Profile Not Found

**Error:** `The config profile (admin-legacy) could not be found`

**Fix:**
```powershell
aws configure --profile admin-legacy
```

### Certificate Not Found

**Error:** `An error occurred (ResourceNotFoundException)`

**Possible causes:**
1. Certificate is in wrong region (must be us-east-1)
2. Certificate domain doesn't match samwylock.com
3. Wrong AWS profile

**Fix:**
```powershell
# List all certificates in admin-legacy
aws acm list-certificates --profile admin-legacy --region us-east-1
```

### Route53 Permission Denied

**Error:** `User: ... is not authorized to perform: route53:ChangeResourceRecordSets`

**Fix:** Add IAM permissions to admin-legacy user:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "route53:GetHostedZone",
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "acm:DescribeCertificate",
        "acm:ListCertificates"
      ],
      "Resource": "*"
    }
  ]
}
```

### DNS Not Resolving

**Symptom:** `api.samwylock.com` doesn't resolve

**Check:**
1. Route53 record was created:
```powershell
aws route53 list-resource-record-sets `
  --hosted-zone-id YOUR_ZONE_ID `
  --profile admin-legacy `
  --query "ResourceRecordSets[?Name=='api.samwylock.com.']"
```

2. DNS propagation (can take 5-10 minutes):
```powershell
nslookup api.samwylock.com
nslookup api.samwylock.com 8.8.8.8  # Use Google DNS
```

### HTTPS Not Working

**Symptom:** Certificate errors or connection refused

**Check:**
1. Certificate status:
```powershell
aws acm describe-certificate `
  --certificate-arn YOUR_ARN `
  --profile admin-legacy `
  --region us-east-1 `
  --query "Certificate.Status"
```

2. ALB listener:
```powershell
aws elbv2 describe-listeners `
  --load-balancer-arn YOUR_ALB_ARN `
  --query "Listeners[?Port==\`443\`]"
```

3. Security group allows port 443

### Terraform Cannot Assume Cross-Account Resources

**Error:** `Error assuming provider configuration`

**This is expected!** The setup does NOT use assume role. It uses **two separate providers**:
- Default provider (primary account)
- admin_legacy provider (personal account)

Both use their own credentials from `~/.aws/credentials`.

---

## Cost Considerations

### ACM Certificate
- ✅ **FREE** (no additional cost)

### Route53
- $0.50/month per hosted zone (already exists)
- $0.40 per million queries (minimal)

### ALB HTTPS
- No additional cost vs HTTP
- Same ALB pricing (~$16/month)

**Total Additional Cost: $0** (using existing certificate and hosted zone)

---

## Security Best Practices

1. ✅ **Use separate AWS accounts** for personal and work resources
2. ✅ **Limit admin-legacy permissions** to only what Terraform needs
3. ✅ **Enable HTTPS redirect** (already configured)
4. ✅ **Use strong certificate** (2048-bit RSA or higher)
5. ✅ **Regular certificate rotation** (ACM handles this automatically)

### Recommended admin-legacy IAM Policy

Create a dedicated IAM user for Terraform in admin-legacy with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "Route53Access",
      "Effect": "Allow",
      "Action": [
        "route53:GetHostedZone",
        "route53:ListHostedZones",
        "route53:ListResourceRecordSets",
        "route53:ChangeResourceRecordSets",
        "route53:GetChange"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ACMReadOnly",
      "Effect": "Allow",
      "Action": [
        "acm:DescribeCertificate",
        "acm:ListCertificates"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Updating the Configuration

### Change Domain Name

1. Update terraform.tfvars:
```hcl
domain_name = "new-api.samwylock.com"
```

2. Run terraform apply:
```powershell
cd terraform
terraform apply
```

This will update the Route53 record to point the new subdomain to the ALB.

### Use Different Certificate

1. Update terraform.tfvars with new certificate ARN:
```hcl
ssl_certificate_arn = "arn:aws:acm:us-east-1:ACCOUNT:certificate/NEW_CERT_ID"
```

2. Run terraform apply:
```powershell
cd terraform
terraform apply
```

### Disable HTTPS (Not Recommended)

To temporarily disable HTTPS:

```hcl
# In terraform.tfvars
ssl_certificate_arn   = ""
enable_https_redirect = false
```

**Note:** This will remove the HTTPS listener and Route53 record.

---

## Summary

✅ **What you get:**
- Custom domain: `api.samwylock.com`
- Free SSL certificate from your admin-legacy account
- Automatic HTTP → HTTPS redirect
- DNS managed in your personal Route53

💰 **Cost:**
- $0 additional (using existing certificate and hosted zone)

🔒 **Security:**
- TLS 1.3 encryption
- Proper domain validation
- Separate account isolation

📝 **Maintenance:**
- Certificate auto-renewed by ACM
- DNS managed in admin-legacy account
- Infrastructure in primary account

---

## Quick Reference Commands

```powershell
# Setup
.\get-cross-account-config.ps1

# Deploy
cd terraform
terraform apply

# Verify
curl https://api.samwylock.com/
nslookup api.samwylock.com

# Check certificate
aws acm describe-certificate --certificate-arn YOUR_ARN --profile admin-legacy --region us-east-1

# Check DNS record
aws route53 list-resource-record-sets --hosted-zone-id YOUR_ZONE_ID --profile admin-legacy --query "ResourceRecordSets[?Name=='api.samwylock.com.']"

# Get ALB URL
terraform output api_url
```

---

**Need help?** Check the troubleshooting section or run `.\get-cross-account-config.ps1` again to verify configuration.

