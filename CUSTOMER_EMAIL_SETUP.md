# Customer Email Notifications

## Current Setup: Cognito Default Email

### How It Works

When an admin creates a customer account, **Cognito automatically sends a welcome email** with the temporary password.

**Email Details:**
- **From:** `no-reply@verificationemail.com` (Cognito default)
- **Subject:** "Welcome to Hovver - Your Account Has Been Created"
- **Contains:**
  - Username (customer's email)
  - Temporary password
  - Instructions to change password on first login

### Email Template

```
Hello {username},

Your Hovver account has been created!

Username: {username}
Temporary Password: {####}

Please log in and change your password on first login.

Best regards,
Hovver Team
```

**Note:** `{username}` and `{####}` are placeholders that Cognito automatically replaces with actual values.

### Admin Workflow

1. **Admin creates customer** via API:
   ```json
   POST /customers
   {
     "email": "customer@example.com",
     "name": "John Doe"
   }
   ```

2. **API returns response:**
   ```json
   {
     "customer_id": "abc123...",
     "email": "customer@example.com",
     "temporary_password": "aB3$xYz9!mN7pQw2",
     ...
   }
   ```

3. **Cognito automatically sends email** to `customer@example.com`

4. **Customer receives email** with:
   - Username: customer@example.com
   - Temporary Password: aB3$xYz9!mN7pQw2

5. **Customer logs in** and must change password

### Why Response Still Includes Password

Even though the email is sent automatically, the API response still includes the `temporary_password` field for:
- **Backup:** In case the email doesn't arrive
- **Admin reference:** Admin can manually share it if needed
- **Logging/auditing:** Can be logged for troubleshooting

## Limitations of Cognito Default Email

⚠️ **Current limitations:**
- Email comes from `no-reply@verificationemail.com` (not your domain)
- Limited customization options
- Basic email template
- No HTML formatting
- Can't add branding/logos
- May end up in spam folders
- Limited to 50 emails per day per user pool (free tier)

## Migration Path: Moving to AWS SES

When you're ready for professional emails, you can migrate to AWS SES (Simple Email Service).

### Benefits of SES

✅ **Custom domain** - Emails from `noreply@hovver.com` or similar
✅ **Full HTML templates** - Professional branding, logos, colors
✅ **Higher limits** - 50,000+ emails per day
✅ **Better deliverability** - Less likely to be marked as spam
✅ **Email analytics** - Track opens, clicks, bounces
✅ **Multiple templates** - Different emails for different scenarios

### Migration Steps (When Ready)

#### 1. Set up SES in AWS

```bash
# Verify your domain in SES
aws ses verify-domain-identity --domain hovver.com --region us-east-1

# Verify individual email addresses for testing
aws ses verify-email-identity --email-address noreply@hovver.com --region us-east-1
```

#### 2. Update Terraform Cognito Configuration

```terraform
# Change email configuration in terraform/cognito.tf
email_configuration {
  email_sending_account = "DEVELOPER"  # Changed from COGNITO_DEFAULT
  source_arn            = "arn:aws:ses:us-east-1:ACCOUNT_ID:identity/hovver.com"
  from_email_address    = "Hovver Team <noreply@hovver.com>"
}
```

#### 3. Create HTML Email Template

Create a professional HTML email template (optional - we can help with this):

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    /* Professional styling */
  </style>
</head>
<body>
  <div style="max-width: 600px; margin: 0 auto;">
    <img src="https://hovver.com/logo.png" alt="Hovver Logo">
    <h1>Welcome to Hovver!</h1>
    <p>Your account has been created...</p>
    <!-- Rest of template -->
  </div>
</body>
</html>
```

#### 4. Update Invite Template

```terraform
admin_create_user_config {
  allow_admin_create_user_only = true
  
  invite_message_template {
    email_subject = "Welcome to Hovver - Your Account Has Been Created"
    # HTML template with full styling
    email_message = file("${path.module}/email-templates/welcome.html")
    sms_message   = "Your Hovver username is {username} and temporary password is {####}"
  }
}
```

#### 5. Add IAM Permissions

The Cognito service needs permission to use SES:

```terraform
# Add to terraform/iam.tf
resource "aws_iam_role" "cognito_ses" {
  name = "${var.project_name}-cognito-ses-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "cognito-idp.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "cognito_ses" {
  role = aws_iam_role.cognito_ses.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ]
      Resource = "*"
    }]
  })
}
```

#### 6. Apply Terraform Changes

```bash
terraform plan
terraform apply
```

## Testing Email Delivery

### Test Cognito Email (Current Setup)

1. Create a test customer with your email:
   ```bash
   POST /customers
   {
     "email": "your-email@example.com",
     "name": "Test User"
   }
   ```

2. Check your inbox for email from `no-reply@verificationemail.com`

3. Verify you receive:
   - Username
   - Temporary password
   - Instructions

### Troubleshooting

**Email not received?**
1. Check spam/junk folder
2. Verify email address is correct
3. Check Cognito CloudWatch logs
4. Ensure email is verified (Cognito requires verification)

**Email in spam?**
- Common with `verificationemail.com` sender
- Solution: Migrate to SES with your domain

## Cost Considerations

### Cognito Default Email (Current)
- **Cost:** Included in Cognito free tier
- **Limit:** 50 emails per day per user pool
- **Overage:** N/A (hard limit)

### AWS SES (Future)
- **Cost:** $0.10 per 1,000 emails
- **Free tier:** 62,000 emails/month (if sending from EC2)
- **No daily limits** (within account limits)

Example:
- 100 customers/month = $0.01
- 1,000 customers/month = $0.10
- 10,000 customers/month = $1.00

Very affordable for most use cases!

## Current Status

✅ **Configured:** Cognito sends automatic welcome emails
✅ **Template:** Custom subject and message
✅ **Delivery:** Via `no-reply@verificationemail.com`
✅ **Ready to deploy:** Terraform configuration updated

📋 **Future Enhancement:** Migrate to SES for professional emails
- Better deliverability
- Custom domain
- HTML templates
- Branding

## Summary

**Current Setup:**
- ✅ Emails sent automatically when customer is created
- ✅ Custom template with temporary password
- ✅ No additional code or services needed
- ⚠️ Limited branding, may go to spam

**Next Steps (Optional):**
1. Deploy current changes (`terraform apply`)
2. Test email delivery
3. When ready, migrate to SES for professional emails

---

**Ready to deploy!** The Cognito email functionality is configured and will work after applying the Terraform changes.
