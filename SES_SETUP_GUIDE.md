# AWS SES Setup Guide for Customer Emails

## Overview

The Hovver Admin Dashboard now uses AWS SES (Simple Email Service) to send professional welcome emails to customers with custom HTML templates.

## Why SES?

✅ **Reliable delivery** - Better deliverability than Cognito default  
✅ **Custom branding** - Professional HTML email templates  
✅ **Your domain** - Emails from `noreply@samwylock.com`  
✅ **No Cognito limitations** - Full control over email content and timing  
✅ **Cost effective** - $0.10 per 1,000 emails  
✅ **Scalable** - 50,000+ emails per day

## Prerequisites

- AWS account with SES access
- Domain name (e.g., samwylock.com)
- DNS access to add verification records

## Setup Steps

### Step 1: Verify Your Domain in SES

#### Option A: Via AWS Console

1. **Go to AWS SES Console**
   - Region: us-east-1 (or your preferred region)
   - Navigate to: Configuration → Verified identities

2. **Create identity**
   - Click "Create identity"
   - Identity type: **Domain**
   - Domain: `samwylock.com`
   - Click "Create identity"

3. **Add DNS records**
   SES will provide DNS records to add to your domain:
   - **DKIM records** (3 CNAME records) - for email authentication
   - **TXT record** - for domain verification

4. **Wait for verification**
   - Usually takes 5-30 minutes
   - Status will change from "Pending" to "Verified"

#### Option B: Via AWS CLI

```bash
# Verify domain
aws ses verify-domain-identity --domain samwylock.com --region us-east-1

# Get DKIM tokens
aws ses verify-domain-dkim --domain samwylock.com --region us-east-1
```

### Step 2: Move Out of SES Sandbox

By default, SES is in sandbox mode with restrictions:
- Can only send to verified email addresses
- Limited to 200 emails per day
- 1 email per second

**Request production access:**

1. **Go to SES Console**
   - Navigate to: Account dashboard

2. **Request production access**
   - Click "Request production access"
   - Fill out the form:
     - **Mail type:** Transactional
     - **Website URL:** https://samwylock.com
     - **Use case description:**
       ```
       Sending welcome emails to customers when their accounts are created,
       and password reset emails. All emails are transactional and sent only
       to users who have requested accounts. Estimated volume: 100-500 emails/month.
       ```
     - **Compliance:** Confirm you comply with policies

3. **Wait for approval**
   - Usually approved within 24 hours
   - You'll receive an email notification

### Step 3: Update Email Service Configuration

Edit `api/services/email.py` and update the sender email:

```python
self.sender_email = "noreply@samwylock.com"  # Change to your verified domain
```

### Step 4: Deploy IAM Permissions

The terraform configuration already includes SES permissions:

```bash
# Assume role
python quick_assume.py arn:aws:iam::ACCOUNT:role/HovverAdminRole

# Apply terraform
cd terraform
terraform apply
```

This adds these permissions to the ECS task role:
- `ses:SendEmail`
- `ses:SendRawEmail`

### Step 5: Test Email Sending

#### Test in Sandbox (Before Production Access)

While in sandbox, you can only send to verified email addresses.

**Verify a test email address:**
```bash
aws ses verify-email-identity --email-address test@example.com --region us-east-1
```

Check email for verification link and click it.

#### Test the API

```bash
# Create a customer
POST /customers
{
  "email": "test@example.com",  # Must be verified in sandbox
  "name": "Test Customer"
}

# Check email inbox for welcome email
```

### Step 6: Monitor Email Sending

**CloudWatch Logs:**
```bash
aws logs tail /aws/ecs/hovver-admin-app --follow --region us-east-1
```

Look for:
```
Email sent successfully. Message ID: 01234567-89ab-cdef-0123-456789abcdef
```

**SES Dashboard:**
- Go to SES Console → Account dashboard
- View sending statistics
- Monitor bounce/complaint rates

## DNS Records Example

After verifying your domain, you'll need to add these records:

### DKIM Records (Email Authentication)
```
Type: CNAME
Name: abc123._domainkey.samwylock.com
Value: abc123.dkim.amazonses.com

Type: CNAME
Name: def456._domainkey.samwylock.com
Value: def456.dkim.amazonses.com

Type: CNAME
Name: ghi789._domainkey.samwylock.com
Value: ghi789.dkim.amazonses.com
```

### Domain Verification
```
Type: TXT
Name: _amazonses.samwylock.com
Value: xyz123verificationtoken456
```

## Email Template Customization

The HTML email template is in `api/services/email.py`. You can customize:

### Colors
```python
.header {
    background-color: #4CAF50;  # Change to your brand color
}
```

### Logo
Add your logo to S3 and include:
```html
<img src="https://your-bucket.s3.amazonaws.com/logo.png" alt="Hovver Logo">
```

### Content
Modify the text in `html_body` and `text_body`:
```python
html_body = f"""
    <p>Welcome to Hovver!</p>
    # Add your custom content here
"""
```

## Troubleshooting

### Error: "Email address is not verified"

**In Sandbox Mode:**
- Verify the recipient email address first
- Or request production access

### Error: "Mail from domain not verified"

**Solution:**
- Complete domain verification in SES Console
- Wait for DNS propagation (up to 72 hours)
- Check DNS records are correct

### Error: "Message rejected"

**Common causes:**
- Recipient email invalid
- Bounce/complaint rate too high
- SES account suspended

**Check:**
```bash
aws ses get-account-sending-enabled --region us-east-1
```

### Emails going to spam

**Solutions:**
1. **Set up SPF record:**
   ```
   Type: TXT
   Name: samwylock.com
   Value: v=spf1 include:amazonses.com ~all
   ```

2. **Set up DMARC:**
   ```
   Type: TXT
   Name: _dmarc.samwylock.com
   Value: v=DMARC1; p=none; rua=mailto:postmaster@samwylock.com
   ```

3. **Warm up your domain:**
   - Start with low volume (10-20 emails/day)
   - Gradually increase over 2-3 weeks

## Cost Estimation

### AWS SES Pricing (us-east-1)
- First 62,000 emails/month: **FREE** (if sending from EC2/ECS)
- After that: **$0.10 per 1,000 emails**

### Examples
- 100 customers/month: **FREE**
- 1,000 customers/month: **FREE**
- 100,000 customers/month: **$3.80/month**

Very affordable! 💰

## Monitoring & Metrics

### Key Metrics to Track

1. **Send rate** - Emails sent per day
2. **Bounce rate** - Should be < 5%
3. **Complaint rate** - Should be < 0.1%
4. **Delivery rate** - Should be > 95%

### Set up CloudWatch Alarms

```bash
# Alert if bounce rate > 5%
aws cloudwatch put-metric-alarm \
  --alarm-name ses-high-bounce-rate \
  --metric-name Reputation.BounceRate \
  --namespace AWS/SES \
  --statistic Average \
  --period 86400 \
  --threshold 0.05 \
  --comparison-operator GreaterThanThreshold
```

## Security Best Practices

✅ **Use IAM policies** - Limit permissions to specific actions  
✅ **Enable DKIM** - Prevents email spoofing  
✅ **Set up SPF** - Authorizes SES to send on your behalf  
✅ **Monitor metrics** - Watch for unusual activity  
✅ **Handle bounces** - Remove invalid addresses  
✅ **Suppress list** - Don't email users who complained  

## Summary Checklist

- [ ] Verify domain in SES
- [ ] Add DNS records (DKIM, verification)
- [ ] Request production access (if needed)
- [ ] Update sender email in code
- [ ] Deploy IAM permissions
- [ ] Test email sending
- [ ] Set up SPF/DMARC records
- [ ] Monitor sending metrics

## Files Modified

✅ **`api/services/email.py`** - New SES email service  
✅ **`api/services/auth.py`** - Uses email service for customer creation and resend  
✅ **`terraform/iam.tf`** - Added SES permissions  
✅ **`api/services/__init__.py`** - Exports email service  

## Quick Start

```bash
# 1. Verify domain in SES Console
#    Region: us-east-1
#    Add DNS records

# 2. Update sender email
#    Edit api/services/email.py
#    Change: self.sender_email = "noreply@samwylock.com"

# 3. Deploy
python quick_assume.py arn:aws:iam::ACCOUNT:role/HovverAdminRole
cd terraform
terraform apply

# 4. Test
POST /customers
{
  "email": "test@example.com",
  "name": "Test User"
}

# 5. Check email inbox!
```

---

**Ready to send professional emails!** 📧✨
