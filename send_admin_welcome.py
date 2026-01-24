#!/usr/bin/env python3
"""
Helper script to create admin users in Cognito and send welcome email.

Usage:
    python send_admin_welcome.py <email> <name>

Example:
    python send_admin_welcome.py john@example.com "John Doe"

This script will:
1. Create a new admin user in Cognito with auto-generated temporary password
2. Add the user to the "Admins" group
3. Send a welcome email with login credentials

Environment Variables Required:
    RESEND_API_KEY: Your Resend API key
    COGNITO_USER_POOL_ID: Cognito User Pool ID
    AWS_REGION: AWS region (default: us-east-1)
    SENDER_EMAIL: Email address to send from (default: noreply@samwylock.com)
    SENDER_NAME: Name to display in sent emails (default: Hover)
    FRONTEND_URL: Frontend URL for login link (default: https://dev.samwylock.com)
"""
import sys
import os
import secrets
import string
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
import resend


# Get the script directory and templates path
SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"


def generate_temporary_password() -> str:
    """
    Generate a secure temporary password that meets Cognito requirements.

    Requirements:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character

    Returns:
        A secure random password string
    """
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "!@#$%^&*"

    # Ensure at least one character from each required set
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special),
    ]

    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special
    password.extend(secrets.choice(all_chars) for _ in range(12))  # Total 16 chars

    # Shuffle to avoid predictable patterns
    secrets.SystemRandom().shuffle(password)

    return ''.join(password)


def create_admin_user(email: str, name: str) -> str:
    """
    Create a new admin user in Cognito and add to Admins group.

    Args:
        email: Admin's email address
        name: Admin's full name

    Returns:
        The auto-generated temporary password

    Raises:
        SystemExit: If user creation fails
    """
    # Get configuration from environment variables
    user_pool_id = os.getenv('COGNITO_USER_POOL_ID')
    if not user_pool_id:
        print("❌ Error: COGNITO_USER_POOL_ID environment variable not set")
        print("Set it with: $env:COGNITO_USER_POOL_ID='your-user-pool-id'")
        sys.exit(1)

    region = os.getenv('AWS_REGION', 'us-east-1')

    # Initialize Cognito client
    try:
        cognito_client = boto3.client('cognito-idp', region_name=region)
    except Exception as e:
        print(f"❌ Error: Failed to initialize AWS Cognito client: {e}")
        print("Make sure you have AWS credentials configured (e.g., via 'aws configure' or IAM role)")
        sys.exit(1)

    # Generate secure temporary password
    temp_password = generate_temporary_password()

    try:
        print(f"Creating admin user in Cognito: {email}...")

        # Prepare user attributes
        user_attributes = [
            {"Name": "email", "Value": email},
            {"Name": "email_verified", "Value": "true"},
            {"Name": "name", "Value": name}
        ]

        # Create user
        response = cognito_client.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=user_attributes,
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # Don't send Cognito email - we'll use Resend
        )

        print(f"✅ User created successfully")

        # Set password as permanent (but still requires change on first login)
        cognito_client.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=email,
            Password=temp_password,
            Permanent=False  # User must change on first login
        )

        print(f"✅ Temporary password set")

        # Add user to Admins group
        try:
            cognito_client.admin_add_user_to_group(
                UserPoolId=user_pool_id,
                Username=email,
                GroupName='Admins'
            )
            print(f"✅ User added to 'Admins' group")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"⚠️  Warning: 'Admins' group not found. Please create it in Cognito console.")
                print(f"   User was created but not added to any group.")
            else:
                raise

        return temp_password

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']

        if error_code == 'UsernameExistsException':
            print(f"❌ Error: User with email {email} already exists in Cognito")
        elif error_code == 'InvalidParameterException':
            print(f"❌ Error: Invalid parameter: {error_message}")
        else:
            print(f"❌ Error creating user in Cognito: {error_code} - {error_message}")

        sys.exit(1)


def send_admin_welcome(email: str, name: str, temp_password: str):
    """
    Send welcome email to a new admin user.

    Args:
        email: Admin's email address
        name: Admin's full name
        temp_password: Temporary password set in Cognito
    """
    # Get configuration from environment variables
    resend_api_key = os.getenv('RESEND_API_KEY')
    if not resend_api_key:
        print("❌ Error: RESEND_API_KEY environment variable not set")
        print("Set it with: $env:RESEND_API_KEY='your-api-key'")
        sys.exit(1)

    sender_email = os.getenv('SENDER_EMAIL', 'noreply@samwylock.com')
    sender_name = os.getenv('SENDER_NAME', 'Hover')
    frontend_url = os.getenv('FRONTEND_URL', 'https://dev.samwylock.com')

    # Initialize Resend
    resend.api_key = resend_api_key

    try:
        print(f"Sending welcome email to {email}...")

        # Load template from file
        template_path = TEMPLATES_DIR / 'admin_welcome.html'
        if not template_path.exists():
            print(f"❌ Error: Template file not found at {template_path}")
            sys.exit(1)

        template = template_path.read_text(encoding='utf-8')

        # Build email
        subject = "Welcome to Hover Admin - Your Account Has Been Created"
        html_body = template.format(
            recipient_name=name,
            recipient_email=email,
            temporary_password=temp_password,
            login_url=frontend_url
        )

        # Send email via Resend
        response = resend.Emails.send({
            "from": f"{sender_name} <{sender_email}>",
            "to": [email],
            "subject": subject,
            "html": html_body,
        })

        email_id = response.get('id')
        print(f"✅ Welcome email sent successfully to {email}")
        print(f"   Email ID: {email_id}")
        print(f"   Admin can now log in at: {frontend_url}")

    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        sys.exit(1)


def main():
    """Main entry point."""
    if len(sys.argv) != 3:
        print("Usage: python send_admin_welcome.py <email> <name>")
        print()
        print("Example:")
        print('  python send_admin_welcome.py john@example.com "John Doe"')
        print()
        print("Environment Variables:")
        print("  RESEND_API_KEY (required)       - Your Resend API key")
        print("  COGNITO_USER_POOL_ID (required) - Cognito User Pool ID")
        print("  AWS_REGION (optional)           - AWS region (default: us-east-1)")
        print("  SENDER_EMAIL (optional)         - Email to send from (default: noreply@samwylock.com)")
        print("  SENDER_NAME (optional)          - Sender name (default: Hover)")
        print("  FRONTEND_URL (optional)         - Frontend URL (default: https://dev.samwylock.com)")
        print()
        print("This script will:")
        print("  1. Create a new admin user in Cognito with auto-generated password")
        print("  2. Add the user to the 'Admins' group")
        print("  3. Send a welcome email with login credentials")
        sys.exit(1)

    email = sys.argv[1]
    name = sys.argv[2]

    # Step 1: Create admin user in Cognito
    temp_password = create_admin_user(email, name)

    # Step 2: Send welcome email
    send_admin_welcome(email, name, temp_password)

    print()
    print("🎉 Admin user created successfully!")
    print(f"   Email: {email}")
    print(f"   Name: {name}")
    print(f"   Welcome email sent with login credentials")


if __name__ == "__main__":
    main()
