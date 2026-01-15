"""
Script to generate temporary AWS access keys by assuming an IAM role.

This script uses AWS STS (Security Token Service) to assume a role and generate
temporary credentials that can be used to access AWS resources.
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class RoleAssumer:
    """Handle AWS role assumption and credential generation."""

    def __init__(
        self,
        role_arn: str,
        session_name: Optional[str] = None,
        duration_seconds: int = 3600,
        region: Optional[str] = None,
        external_id: Optional[str] = None,
        mfa_serial: Optional[str] = None,
        mfa_token: Optional[str] = None,
    ):
        """
        Initialize the RoleAssumer.

        Args:
            role_arn: The ARN of the role to assume
            session_name: An identifier for the assumed session (defaults to timestamp)
            duration_seconds: Duration of temporary credentials (900-43200 seconds)
            region: AWS region (defaults to environment or us-east-1)
            external_id: External ID for role assumption (if required by role)
            mfa_serial: MFA device serial number (if MFA is required)
            mfa_token: Current MFA token code (if MFA is required)
        """
        self.role_arn = role_arn
        self.session_name = session_name or f"AssumeRoleSession-{int(datetime.now().timestamp())}"
        self.duration_seconds = max(900, min(43200, duration_seconds))  # Clamp between 15 min - 12 hours
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.external_id = external_id
        self.mfa_serial = mfa_serial
        self.mfa_token = mfa_token

        # Initialize STS client
        self.sts_client = boto3.client("sts", region_name=self.region)

    def assume_role(self) -> dict:
        """
        Assume the specified IAM role and return temporary credentials.

        Returns:
            Dictionary containing temporary credentials and metadata

        Raises:
            ClientError: If the role assumption fails
            NoCredentialsError: If AWS credentials are not configured
        """
        try:
            # Build the assume_role parameters
            assume_role_params = {
                "RoleArn": self.role_arn,
                "RoleSessionName": self.session_name,
                "DurationSeconds": self.duration_seconds,
            }

            # Add optional parameters if provided
            if self.external_id:
                assume_role_params["ExternalId"] = self.external_id

            if self.mfa_serial and self.mfa_token:
                assume_role_params["SerialNumber"] = self.mfa_serial
                assume_role_params["TokenCode"] = self.mfa_token

            # Assume the role
            response = self.sts_client.assume_role(**assume_role_params)

            credentials = response["Credentials"]
            assumed_role = response["AssumedRoleUser"]

            return {
                "AccessKeyId": credentials["AccessKeyId"],
                "SecretAccessKey": credentials["SecretAccessKey"],
                "SessionToken": credentials["SessionToken"],
                "Expiration": credentials["Expiration"].isoformat(),
                "AssumedRoleArn": assumed_role["Arn"],
                "AssumedRoleId": assumed_role["AssumedRoleId"],
            }

        except NoCredentialsError:
            print("ERROR: No AWS credentials found. Please configure your AWS credentials.", file=sys.stderr)
            raise
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            print(f"ERROR: Failed to assume role: {error_code} - {error_message}", file=sys.stderr)
            raise

    def print_credentials(self, credentials: dict, format: str = "text") -> None:
        """
        Print the temporary credentials in various formats.

        Args:
            credentials: Dictionary containing the temporary credentials
            format: Output format - 'text', 'json', 'env', or 'export'
        """
        if format == "json":
            print(json.dumps(credentials, indent=2))

        elif format == "env":
            # Windows-style environment variables
            print(f"AWS_ACCESS_KEY_ID={credentials['AccessKeyId']}")
            print(f"AWS_SECRET_ACCESS_KEY={credentials['SecretAccessKey']}")
            print(f"AWS_SESSION_TOKEN={credentials['SessionToken']}")
            print(f"# Expires at: {credentials['Expiration']}")

        elif format == "export":
            # Unix-style export commands
            print(f"export AWS_ACCESS_KEY_ID={credentials['AccessKeyId']}")
            print(f"export AWS_SECRET_ACCESS_KEY={credentials['SecretAccessKey']}")
            print(f"export AWS_SESSION_TOKEN={credentials['SessionToken']}")
            print(f"# Expires at: {credentials['Expiration']}")

        elif format == "powershell":
            # PowerShell-style environment variables
            print(f"$env:AWS_ACCESS_KEY_ID='{credentials['AccessKeyId']}'")
            print(f"$env:AWS_SECRET_ACCESS_KEY='{credentials['SecretAccessKey']}'")
            print(f"$env:AWS_SESSION_TOKEN='{credentials['SessionToken']}'")
            print(f"# Expires at: {credentials['Expiration']}")

        else:  # text format
            print("=" * 80)
            print("TEMPORARY AWS CREDENTIALS")
            print("=" * 80)
            print(f"Access Key ID:     {credentials['AccessKeyId']}")
            print(f"Secret Access Key: {credentials['SecretAccessKey']}")
            print(f"Session Token:     {credentials['SessionToken']}")
            print(f"Expiration:        {credentials['Expiration']}")
            print(f"Assumed Role ARN:  {credentials['AssumedRoleArn']}")
            print(f"Assumed Role ID:   {credentials['AssumedRoleId']}")
            print("=" * 80)

    def save_to_env_file(self, credentials: dict, filename: str = ".env.assumed") -> None:
        """
        Save the temporary credentials to an environment file.

        Args:
            credentials: Dictionary containing the temporary credentials
            filename: Name of the file to save credentials to
        """
        try:
            with open(filename, "w") as f:
                f.write(f"# Temporary AWS Credentials\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Expires: {credentials['Expiration']}\n")
                f.write(f"# Role: {credentials['AssumedRoleArn']}\n\n")
                f.write(f"AWS_ACCESS_KEY_ID={credentials['AccessKeyId']}\n")
                f.write(f"AWS_SECRET_ACCESS_KEY={credentials['SecretAccessKey']}\n")
                f.write(f"AWS_SESSION_TOKEN={credentials['SessionToken']}\n")
            print(f"\nCredentials saved to: {filename}")
        except IOError as e:
            print(f"ERROR: Failed to save credentials to file: {e}", file=sys.stderr)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate temporary AWS access keys by assuming an IAM role",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python assume_role.py arn:aws:iam::123456789012:role/MyRole

  # With custom session name and duration
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --session-name MySession --duration 7200

  # With external ID (for cross-account access)
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --external-id my-external-id

  # With MFA
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --mfa-serial arn:aws:iam::123456789012:mfa/user --mfa-token 123456

  # Output as JSON
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --format json

  # Output as PowerShell commands (for Windows)
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --format powershell

  # Save to environment file
  python assume_role.py arn:aws:iam::123456789012:role/MyRole \\
    --save-to-file .env.assumed
        """
    )

    parser.add_argument(
        "role_arn",
        help="The ARN of the IAM role to assume (e.g., arn:aws:iam::123456789012:role/MyRole)"
    )

    parser.add_argument(
        "--session-name",
        help="Name for the assumed role session (default: auto-generated timestamp)"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Duration of temporary credentials in seconds (900-43200, default: 3600)"
    )

    parser.add_argument(
        "--region",
        help="AWS region (default: from AWS_REGION env var or us-east-1)"
    )

    parser.add_argument(
        "--external-id",
        help="External ID for role assumption (if required by the role trust policy)"
    )

    parser.add_argument(
        "--mfa-serial",
        help="MFA device serial number (e.g., arn:aws:iam::123456789012:mfa/user)"
    )

    parser.add_argument(
        "--mfa-token",
        help="Current MFA token code (6-digit code from your MFA device)"
    )

    parser.add_argument(
        "--format",
        choices=["text", "json", "env", "export", "powershell"],
        default="text",
        help="Output format (default: text)"
    )

    parser.add_argument(
        "--save-to-file",
        metavar="FILENAME",
        help="Save credentials to an environment file"
    )

    args = parser.parse_args()

    # Create role assumer instance
    assumer = RoleAssumer(
        role_arn=args.role_arn,
        session_name=args.session_name,
        duration_seconds=args.duration,
        region=args.region,
        external_id=args.external_id,
        mfa_serial=args.mfa_serial,
        mfa_token=args.mfa_token,
    )

    try:
        # Assume the role
        credentials = assumer.assume_role()

        # Print credentials in requested format
        assumer.print_credentials(credentials, format=args.format)

        # Save to file if requested
        if args.save_to_file:
            assumer.save_to_env_file(credentials, args.save_to_file)

        return 0

    except Exception as e:
        print(f"\nFailed to assume role: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

