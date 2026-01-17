#!/usr/bin/env python3
"""
Verify an email address for SES sandbox testing
"""
import boto3
import sys

def verify_email(email_address):
    """Verify an email address for SES"""
    ses = boto3.client('ses', region_name='us-east-1')

    print(f"\n{'='*70}")
    print(f"  VERIFYING EMAIL ADDRESS FOR SES")
    print(f"{'='*70}\n")

    print(f"Email: {email_address}")
    print(f"Region: us-east-1")
    print()

    try:
        # Send verification email
        response = ses.verify_email_identity(EmailAddress=email_address)

        print("✅ Verification email sent successfully!")
        print()
        print("Next steps:")
        print(f"  1. Check inbox: {email_address}")
        print("  2. Look for email from: no-reply-aws@amazon.com")
        print("  3. Subject: 'Amazon SES Email Address Verification Request'")
        print("  4. Click the verification link in the email")
        print("  5. Wait 1-2 minutes")
        print("  6. Try creating a customer again")
        print()
        print("To check verification status:")
        print(f"  aws ses get-identity-verification-attributes \\")
        print(f"    --identities {email_address} --region us-east-1")
        print()

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python verify_test_email.py <email-address>")
        print("\nExample:")
        print("  python verify_test_email.py sjw787.sw+test@gmail.com")
        print()
        sys.exit(1)

    email = sys.argv[1]
    verify_email(email)
