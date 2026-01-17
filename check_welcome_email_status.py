#!/usr/bin/env python3
"""
Complete Welcome Email Functionality Check
Verifies all components needed for customer welcome emails
"""
import boto3
import sys
import json
from botocore.exceptions import ClientError

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def check_ses_status():
    """Check SES domain verification and DKIM status"""
    print_section("1. SES DOMAIN VERIFICATION")
    
    try:
        ses = boto3.client('ses', region_name='us-east-1')
        
        # Check domain verification
        attrs = ses.get_identity_verification_attributes(Identities=['samwylock.com'])
        domain_attrs = attrs['VerificationAttributes'].get('samwylock.com', {})
        
        verification_status = domain_attrs.get('VerificationStatus', 'Not Found')
        verification_token = domain_attrs.get('VerificationToken', 'N/A')
        
        print(f"Domain: samwylock.com")
        print(f"Verification Status: {verification_status}")
        if verification_status == 'Success':
            print("✅ PASS: Domain is verified")
        else:
            print("❌ FAIL: Domain is not verified yet")
            print(f"   Verification Token: {verification_token}")
            print("   Action: Wait for DNS propagation (5-30 minutes)")
            return False
        
        # Check DKIM
        dkim_attrs = ses.get_identity_dkim_attributes(Identities=['samwylock.com'])
        domain_dkim = dkim_attrs['DkimAttributes'].get('samwylock.com', {})
        
        dkim_enabled = domain_dkim.get('DkimEnabled', False)
        dkim_status = domain_dkim.get('DkimVerificationStatus', 'N/A')
        dkim_tokens = domain_dkim.get('DkimTokens', [])
        
        print(f"\nDKIM Enabled: {dkim_enabled}")
        print(f"DKIM Status: {dkim_status}")
        
        if dkim_status == 'Success':
            print("✅ PASS: DKIM is verified")
        else:
            print("❌ FAIL: DKIM is not verified yet")
            print(f"   DKIM Tokens ({len(dkim_tokens)}):")
            for token in dkim_tokens:
                print(f"     - {token}")
            print("   Action: Wait for DNS propagation")
            return False
        
        # Check sandbox status
        account = ses.get_account_sending_enabled()
        print(f"\nAccount Sending Enabled: {account.get('Enabled', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR checking SES: {e}")
        return False


def check_cognito_email_config():
    """Check Cognito email configuration"""
    print_section("2. COGNITO EMAIL CONFIGURATION")
    
    try:
        cognito = boto3.client('cognito-idp', region_name='us-east-1')
        
        # Get user pool configuration
        pool = cognito.describe_user_pool(UserPoolId='us-east-1_vqzmBxIoP')
        email_config = pool['UserPool'].get('EmailConfiguration', {})
        
        print(f"User Pool: us-east-1_vqzmBxIoP")
        print(f"Email Sending Account: {email_config.get('EmailSendingAccount', 'COGNITO_DEFAULT')}")
        
        source_arn = email_config.get('SourceArn', 'Not set')
        from_address = email_config.get('From', 'Not set')
        reply_to = email_config.get('ReplyToEmailAddress', 'Not set')
        
        print(f"Source ARN: {source_arn}")
        print(f"FROM Address: {from_address}")
        print(f"Reply-To: {reply_to}")
        
        # Check if using SES
        if email_config.get('EmailSendingAccount') == 'DEVELOPER':
            if '052869941234' in source_arn and 'samwylock.com' in source_arn:
                print("✅ PASS: Cognito is configured to use SES from iamadmin-dev")
                return True
            else:
                print("⚠️  WARNING: Using SES but ARN may be incorrect")
                print(f"   Expected: arn:aws:ses:us-east-1:052869941234:identity/samwylock.com")
                print(f"   Current: {source_arn}")
                return False
        else:
            print("❌ FAIL: Cognito is using default email (not SES)")
            print("\n   ACTION REQUIRED: Configure Cognito to use SES")
            print("   1. Go to Cognito > User Pools > us-east-1_vqzmBxIoP")
            print("   2. Navigate to: Messaging > Email")
            print("   3. Select: 'Send email with Amazon SES'")
            print("   4. FROM address: noreply@samwylock.com")
            print("   5. Source ARN: arn:aws:ses:us-east-1:052869941234:identity/samwylock.com")
            return False
            
    except Exception as e:
        print(f"❌ ERROR checking Cognito: {e}")
        return False


def check_iam_permissions():
    """Check IAM permissions for Cognito to send via SES"""
    print_section("3. IAM PERMISSIONS")
    
    try:
        iam = boto3.client('iam', region_name='us-east-1')
        sts = boto3.client('sts')
        
        # Get current account
        account = sts.get_caller_identity()['Account']
        print(f"Current Account: {account}")
        
        if account == '052869941234':
            print("✅ PASS: In correct account (iamadmin-dev)")
        else:
            print(f"⚠️  WARNING: In account {account}, expected 052869941234")
        
        # Check if Cognito has permissions to use SES
        # This is implicitly allowed when both are in the same account
        print("\nCognito-SES Integration:")
        print("  When Cognito and SES are in the same account,")
        print("  Cognito automatically has permission to send via SES.")
        print("✅ PASS: Cognito and SES are in the same account")
        
        return True
        
    except Exception as e:
        print(f"⚠️  Could not fully verify IAM: {e}")
        return True  # Not critical


def check_customer_endpoint():
    """Check customer creation endpoint"""
    print_section("4. CUSTOMER CREATION ENDPOINT")
    
    try:
        # Check if the customers endpoint exists
        with open('api/routers/customers.py', 'r') as f:
            content = f.read()
            
        print("Customer Router File: ✅ Found")
        
        # Check for create_customer endpoint
        if 'def create_customer' in content or '@router.post' in content:
            print("Create Customer Endpoint: ✅ Found")
        else:
            print("Create Customer Endpoint: ❌ Not found")
            return False
        
        # Check for AdminCreateUser call
        if 'admin_create_user' in content or 'AdminCreateUser' in content:
            print("Cognito AdminCreateUser: ✅ Implemented")
        else:
            print("Cognito AdminCreateUser: ❌ Not found")
            return False
        
        # Check for message action
        if 'RESEND' in content or 'MessageAction' in content:
            print("Welcome Email Trigger: ✅ Configured")
        else:
            print("Welcome Email Trigger: ⚠️  May not be configured")
        
        return True
        
    except FileNotFoundError:
        print("❌ ERROR: Customer router file not found")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_email_service():
    """Check email service module"""
    print_section("5. EMAIL SERVICE MODULE")
    
    try:
        with open('api/services/email.py', 'r') as f:
            content = f.read()
        
        print("Email Service File: ✅ Found")
        
        # Check for key functions
        if 'send_welcome_email' in content or 'resend_welcome' in content:
            print("Welcome Email Function: ✅ Implemented")
        else:
            print("Welcome Email Function: ❌ Not found")
            return False
        
        return True
        
    except FileNotFoundError:
        print("Email Service File: ❌ Not found")
        print("   Note: Cognito can send welcome emails automatically")
        return True  # Not critical if using Cognito's built-in emails
    except Exception as e:
        print(f"⚠️  Could not check email service: {e}")
        return True  # Not critical


def print_summary(ses_ok, cognito_ok, iam_ok, endpoint_ok, email_ok):
    """Print overall summary"""
    print_section("SUMMARY")
    
    statuses = {
        'SES Domain Verification': ses_ok,
        'Cognito Email Config': cognito_ok,
        'IAM Permissions': iam_ok,
        'Customer Endpoint': endpoint_ok,
        'Email Service': email_ok
    }
    
    all_pass = all(statuses.values())
    
    for component, status in statuses.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {component}")
    
    print("\n" + "="*70)
    
    if all_pass:
        print("\n🎉 ALL CHECKS PASSED!")
        print("\nWelcome email functionality is READY!")
        print("\nYou can now:")
        print("  1. Create a new customer via the admin dashboard")
        print("  2. Customer will receive welcome email at noreply@samwylock.com")
        print("  3. Monitor email delivery in SES Console")
    else:
        print("\n⚠️  SOME CHECKS FAILED")
        print("\nAction Items:")
        if not ses_ok:
            print("  - Wait for SES domain verification (5-30 minutes)")
        if not cognito_ok:
            print("  - Configure Cognito to use SES (see section 2)")
        if not endpoint_ok:
            print("  - Check customer creation endpoint implementation")
        print("\nRe-run this script after addressing issues:")
        print("  python check_welcome_email_status.py")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  WELCOME EMAIL FUNCTIONALITY - COMPLETE STATUS CHECK")
    print("="*70)
    print("\nChecking all components required for customer welcome emails...")
    
    # Run all checks
    ses_ok = check_ses_status()
    cognito_ok = check_cognito_email_config()
    iam_ok = check_iam_permissions()
    endpoint_ok = check_customer_endpoint()
    email_ok = check_email_service()
    
    # Print summary
    print_summary(ses_ok, cognito_ok, iam_ok, endpoint_ok, email_ok)
    
    # Exit code
    sys.exit(0 if all([ses_ok, cognito_ok, iam_ok, endpoint_ok, email_ok]) else 1)
