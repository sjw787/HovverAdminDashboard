#!/usr/bin/env python3
"""
Configure Cognito User Pool to use SES for email sending
"""
import boto3
from botocore.exceptions import ClientError

USER_POOL_ID = "us-east-1_vqzmBxIoP"
REGION = "us-east-1"
ACCOUNT_ID = "052869941234"
FROM_EMAIL = "noreply@samwylock.com"
DOMAIN = "samwylock.com"

def configure_cognito_ses():
    """Configure Cognito to use SES for sending emails"""

    print("="*70)
    print("  CONFIGURE COGNITO TO USE SES")
    print("="*70)
    print()

    cognito = boto3.client('cognito-idp', region_name=REGION)

    try:
        # Get current configuration
        print(f"Checking User Pool: {USER_POOL_ID}")
        pool = cognito.describe_user_pool(UserPoolId=USER_POOL_ID)
        current_email_config = pool['UserPool'].get('EmailConfiguration', {})

        print(f"Current Email Sending Account: {current_email_config.get('EmailSendingAccount', 'COGNITO_DEFAULT')}")
        print()

        # Prepare SES email configuration
        source_arn = f"arn:aws:ses:{REGION}:{ACCOUNT_ID}:identity/{DOMAIN}"

        email_configuration = {
            'SourceArn': source_arn,
            'EmailSendingAccount': 'DEVELOPER',
            'From': FROM_EMAIL
        }

        print("Updating Cognito with SES configuration:")
        print(f"  Source ARN: {source_arn}")
        print(f"  FROM Email: {FROM_EMAIL}")
        print(f"  Email Sending Account: DEVELOPER")
        print()

        # Update the user pool
        response = cognito.update_user_pool(
            UserPoolId=USER_POOL_ID,
            EmailConfiguration=email_configuration
        )

        print("✅ SUCCESS!")
        print()
        print("Cognito is now configured to send emails via SES!")
        print()
        print("Verification:")

        # Verify the update
        pool = cognito.describe_user_pool(UserPoolId=USER_POOL_ID)
        new_email_config = pool['UserPool'].get('EmailConfiguration', {})

        print(f"  Email Sending Account: {new_email_config.get('EmailSendingAccount')}")
        print(f"  Source ARN: {new_email_config.get('SourceArn')}")
        print(f"  FROM Address: {new_email_config.get('From')}")
        print()

        print("Next Steps:")
        print("  1. Test by creating a new customer")
        print("  2. Customer will receive welcome email from", FROM_EMAIL)
        print("  3. Monitor delivery in SES Console > Email sending > Dashboard")
        print()

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        print(f"❌ ERROR: {error_code}")
        print(f"   {error_message}")
        print()

        if 'SourceArn' in error_message or 'SES' in error_message:
            print("Possible issues:")
            print("  - SES domain not verified yet")
            print("  - SES identity ARN incorrect")
            print("  - Region mismatch")
            print()
            print("Check SES status:")
            print("  python setup_ses.py --check-status samwylock.com")

        return False

    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False


if __name__ == "__main__":
    print()
    success = configure_cognito_ses()

    if success:
        print("="*70)
        print("  RUN COMPLETE STATUS CHECK")
        print("="*70)
        print()
        print("Verify everything is working:")
        print("  python check_welcome_email_status.py")
        print()
    else:
        print("="*70)
        print("  CONFIGURATION FAILED")
        print("="*70)
        print()
        print("Please resolve the issues above and try again.")
        print()
