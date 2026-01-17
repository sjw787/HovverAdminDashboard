# SES and DNS Setup Scripts

Automated scripts to set up AWS SES email sending with proper DNS configuration.

## 📁 Scripts Included

1. **`setup_ses.py`** - Python script for SES setup and management
2. **`setup_dns.ps1`** - PowerShell script for DNS record configuration
3. **`SES_SETUP_GUIDE.md`** - Complete manual setup guide

## 🚀 Quick Start

### Option 1: Fully Automated (Route 53)

If your domain is hosted in AWS Route 53:

```powershell
# 1. Set up SES and get DNS records, then apply them to Route 53
.\setup_dns.ps1 -Domain "samwylock.com" -Route53

# 2. Check verification status (wait 5-30 minutes)
python setup_ses.py --check-status samwylock.com

# 3. Done! ✅
```

### Option 2: Semi-Automated (Any DNS Provider)

For Cloudflare, GoDaddy, Namecheap, etc.:

```powershell
# 1. Get DNS records from SES
python setup_ses.py --domain samwylock.com

# 2. Copy/paste the records into your DNS provider's dashboard
# (Script will show formatted instructions)

# 3. Wait 5-30 minutes, then check status
python setup_ses.py --check-status samwylock.com
```

## 📖 Detailed Usage

### Python Script: `setup_ses.py`

#### Verify a Domain

```bash
python setup_ses.py --domain samwylock.com
```

**Output:**
- Domain verification token (TXT record)
- 3 DKIM tokens (CNAME records)
- SPF record recommendation
- DMARC record recommendation
- Option to save to file

#### Verify an Email (for testing in sandbox)

```bash
python setup_ses.py --verify-email test@example.com
```

Sends verification email to the address. Click the link to verify.

#### Check Verification Status

```bash
python setup_ses.py --check-status samwylock.com
```

Shows current verification status:
- ✅ Success - Domain is verified
- ⏳ Pending - DNS records not yet propagated
- ❌ Failed - Check DNS configuration

#### List All Verified Identities

```bash
python setup_ses.py --list
```

Shows all verified domains and email addresses.

#### Check Sandbox Status

```bash
python setup_ses.py --sandbox-status
```

Shows:
- Current sending limits
- Whether you're in sandbox mode
- Instructions to request production access

#### Save DNS Instructions to File

```bash
python setup_ses.py --domain samwylock.com --output-dns dns_records.txt
```

### PowerShell Script: `setup_dns.ps1`

#### Automatic Route 53 Setup

```powershell
# Add DNS records to Route 53
.\setup_dns.ps1 -Domain "samwylock.com" -Route53

# Dry run (preview without making changes)
.\setup_dns.ps1 -Domain "samwylock.com" -Route53 -DryRun
```

#### Manual DNS Setup (Any Provider)

```powershell
# Show DNS records to add manually
.\setup_dns.ps1 -Domain "samwylock.com" -Provider "manual"

# Or just
.\setup_dns.ps1 -Domain "samwylock.com"
```

#### Show Help

```powershell
.\setup_dns.ps1 -ShowInstructions
```

## 📋 Complete Setup Workflow

### Step 1: Initial SES Setup

```bash
# Get DNS records
python setup_ses.py --domain samwylock.com

# Or save to file
python setup_ses.py --domain samwylock.com --output-dns ses_records.txt
```

### Step 2: Add DNS Records

**Option A: Route 53 (Automatic)**
```powershell
.\setup_dns.ps1 -Domain "samwylock.com" -Route53
```

**Option B: Other DNS Provider (Manual)**

The Python script shows you exactly what to add. For example:

```
Type:  TXT
Name:  _amazonses.samwylock.com
Value: abc123xyz...
TTL:   300
```

Copy these into your DNS provider's dashboard (Cloudflare, GoDaddy, etc.)

### Step 3: Wait for Verification

```bash
# Check status every few minutes
python setup_ses.py --check-status samwylock.com

# When status shows "Success", you're ready! ✅
```

### Step 4: Request Production Access (Optional)

```bash
# Check if you're in sandbox
python setup_ses.py --sandbox-status

# If in sandbox, request production access via AWS Console:
# SES → Account dashboard → Request production access
```

### Step 5: Test Email Sending

```bash
# While in sandbox, verify test email first
python setup_ses.py --verify-email test@example.com

# Create a customer via API
POST /customers
{
  "email": "test@example.com",
  "name": "Test User"
}

# Check inbox! 📧
```

## 🔧 Prerequisites

### Required

- **AWS CLI** configured with credentials
  ```bash
  aws configure
  ```

- **Python 3.7+** with boto3
  ```bash
  pip install boto3
  ```

- **PowerShell** (for DNS script, Windows has it by default)

### Permissions Required

Your AWS user/role needs these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:VerifyDomainIdentity",
        "ses:VerifyDomainDkim",
        "ses:VerifyEmailIdentity",
        "ses:GetIdentityVerificationAttributes",
        "ses:ListIdentities",
        "ses:ListVerifiedEmailAddresses",
        "ses:GetAccountSendingEnabled",
        "ses:GetSendQuota"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "route53:ListHostedZones",
        "route53:ChangeResourceRecordSets"
      ],
      "Resource": "*"
    }
  ]
}
```

## 📊 DNS Records Explained

### 1. Domain Verification (TXT)

```
Name:  _amazonses.samwylock.com
Value: verification_token_from_ses
```

**Purpose:** Proves you own the domain

### 2. DKIM Records (3 CNAME)

```
Name:  token1._domainkey.samwylock.com
Value: token1.dkim.amazonses.com

Name:  token2._domainkey.samwylock.com
Value: token2.dkim.amazonses.com

Name:  token3._domainkey.samwylock.com
Value: token3.dkim.amazonses.com
```

**Purpose:** Email authentication, prevents spoofing

### 3. SPF Record (TXT) - Recommended

```
Name:  samwylock.com
Value: v=spf1 include:amazonses.com ~all
```

**Purpose:** Authorizes SES to send on your behalf

### 4. DMARC Record (TXT) - Recommended

```
Name:  _dmarc.samwylock.com
Value: v=DMARC1; p=none; rua=mailto:postmaster@samwylock.com
```

**Purpose:** Email authentication policy, improves deliverability

## 🐛 Troubleshooting

### "Email address is not verified"

**In Sandbox Mode:**
```bash
# Verify the recipient email
python setup_ses.py --verify-email recipient@example.com
```

**Or:** Request production access

### "Domain verification pending"

**Check DNS propagation:**
```bash
# Windows
nslookup -type=TXT _amazonses.samwylock.com

# Mac/Linux
dig TXT _amazonses.samwylock.com
```

**Wait:** DNS can take up to 72 hours (usually 5-30 minutes)

### "Hosted zone not found" (Route 53)

```bash
# Check your hosted zones
aws route53 list-hosted-zones

# Make sure domain ends with a dot in Route 53
# Correct: samwylock.com.
# Wrong: samwylock.com
```

### Script errors

```bash
# Check AWS CLI is configured
aws sts get-caller-identity

# Check region
aws configure get region

# Test SES access
aws ses list-identities --region us-east-1
```

## 📈 After Setup

### Update Application Code

Edit `api/services/email.py`:

```python
self.sender_email = "noreply@samwylock.com"  # Your verified domain
```

### Deploy

```bash
python quick_assume.py arn:aws:iam::ACCOUNT:role/HovverAdminRole
cd terraform
terraform apply
```

### Monitor

```bash
# Check CloudWatch logs
aws logs tail /aws/ecs/hovver-admin-app --follow --region us-east-1

# Check SES dashboard
# AWS Console → SES → Account dashboard
```

## 💰 Cost

- **SES Setup:** FREE
- **DNS Records:** FREE (in Route 53: $0.50/month per hosted zone)
- **Sending Emails:** First 62,000/month FREE, then $0.10/1,000

## 🔗 Additional Resources

- [SES_SETUP_GUIDE.md](SES_SETUP_GUIDE.md) - Complete manual setup guide
- [AWS SES Documentation](https://docs.aws.amazon.com/ses/)
- [DNS Record Types](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/ResourceRecordTypes.html)

## 🎯 Examples

### Complete Automated Setup (Route 53)

```powershell
# One command setup
.\setup_dns.ps1 -Domain "samwylock.com" -Route53

# Wait and check
Start-Sleep -Seconds 300  # Wait 5 minutes
python setup_ses.py --check-status samwylock.com
```

### Manual Setup with File Output

```bash
# Generate DNS instructions
python setup_ses.py --domain samwylock.com --output-dns instructions.txt

# Review the file
cat instructions.txt  # or 'type instructions.txt' on Windows

# Add records to your DNS provider
# Then check status
python setup_ses.py --check-status samwylock.com
```

### Sandbox Testing

```bash
# Verify test email
python setup_ses.py --verify-email test@example.com

# Check sandbox status
python setup_ses.py --sandbox-status

# Test via API
curl -X POST https://api.samwylock.com/customers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"email":"test@example.com","name":"Test User"}'
```

## ✅ Success Checklist

- [ ] Python script runs without errors
- [ ] Domain verification token obtained
- [ ] 3 DKIM tokens obtained
- [ ] DNS records added (Route 53 or manual)
- [ ] Verification status shows "Success"
- [ ] SPF record added (optional but recommended)
- [ ] DMARC record added (optional but recommended)
- [ ] Sender email updated in code
- [ ] Terraform deployed with SES permissions
- [ ] Test email received successfully
- [ ] Production access requested (if needed)

---

**Ready to send professional emails!** 📧✨

For questions or issues, refer to the [complete setup guide](SES_SETUP_GUIDE.md).
