"""
Helper script to quickly assume a role and update environment variables.
Integrates with the Hovver Admin Dashboard configuration.
"""
import argparse
import sys
from pathlib import Path

try:
    from assume_role import RoleAssumer
except ImportError as e:
    print(f"ERROR: Could not import assume_role module: {e}", file=sys.stderr)
    print("Make sure assume_role.py is in the same directory.", file=sys.stderr)
    sys.exit(1)


def update_env_file(credentials: dict, env_file: str = ".env", backup: bool = True) -> None:
    """
    Update the .env file with temporary credentials.

    Args:
        credentials: Dictionary containing temporary credentials
        env_file: Path to the .env file
        backup: Whether to create a backup of the original file
    """
    env_path = Path(env_file)

    if not env_path.exists():
        print(f"ERROR: {env_file} not found", file=sys.stderr)
        sys.exit(1)

    # Create backup if requested
    if backup:
        backup_path = env_path.with_suffix('.env.backup')
        backup_path.write_text(env_path.read_text())
        print(f"Backup created: {backup_path}")

    # Read existing .env file
    lines = env_path.read_text().splitlines()

    # Update or add AWS credentials
    updated = {
        'AWS_ACCESS_KEY_ID': False,
        'AWS_SECRET_ACCESS_KEY': False,
        'AWS_SESSION_TOKEN': False
    }

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('AWS_ACCESS_KEY_ID='):
            new_lines.append(f"AWS_ACCESS_KEY_ID={credentials['AccessKeyId']}")
            updated['AWS_ACCESS_KEY_ID'] = True
        elif stripped.startswith('AWS_SECRET_ACCESS_KEY='):
            new_lines.append(f"AWS_SECRET_ACCESS_KEY={credentials['SecretAccessKey']}")
            updated['AWS_SECRET_ACCESS_KEY'] = True
        elif stripped.startswith('AWS_SESSION_TOKEN='):
            new_lines.append(f"AWS_SESSION_TOKEN={credentials['SessionToken']}")
            updated['AWS_SESSION_TOKEN'] = True
        else:
            new_lines.append(line)

    # Add any missing credentials
    if not updated['AWS_ACCESS_KEY_ID']:
        new_lines.append(f"AWS_ACCESS_KEY_ID={credentials['AccessKeyId']}")
    if not updated['AWS_SECRET_ACCESS_KEY']:
        new_lines.append(f"AWS_SECRET_ACCESS_KEY={credentials['SecretAccessKey']}")
    if not updated['AWS_SESSION_TOKEN']:
        new_lines.append(f"AWS_SESSION_TOKEN={credentials['SessionToken']}")

    # Add expiration comment
    new_lines.append(f"# Credentials expire at: {credentials['Expiration']}")

    # Write back to file
    env_path.write_text('\n'.join(new_lines) + '\n')
    print(f"✓ Updated {env_file} with temporary credentials")
    print(f"✓ Expires at: {credentials['Expiration']}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Quick helper to assume a role and update .env file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update .env with temporary credentials
  python quick_assume.py arn:aws:iam::123456789012:role/HovverAdminRole

  # Update custom env file
  python quick_assume.py arn:aws:iam::123456789012:role/HovverAdminRole --env-file .env.production

  # With MFA
  python quick_assume.py arn:aws:iam::123456789012:role/SecureRole \\
    --mfa-serial arn:aws:iam::123456789012:mfa/user --mfa-token 123456

  # No backup
  python quick_assume.py arn:aws:iam::123456789012:role/HovverAdminRole --no-backup
        """
    )

    parser.add_argument(
        "role_arn",
        help="The ARN of the IAM role to assume"
    )

    parser.add_argument(
        "--env-file",
        default=".env",
        help="Path to .env file (default: .env)"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create a backup of the original .env file"
    )

    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Duration in seconds (default: 3600)"
    )

    parser.add_argument(
        "--session-name",
        help="Session name (default: auto-generated)"
    )

    parser.add_argument(
        "--external-id",
        help="External ID for role assumption"
    )

    parser.add_argument(
        "--mfa-serial",
        help="MFA device serial number"
    )

    parser.add_argument(
        "--mfa-token",
        help="Current MFA token code"
    )

    parser.add_argument(
        "--region",
        help="AWS region"
    )

    args = parser.parse_args()

    print(f"Assuming role: {args.role_arn}")

    # Create role assumer
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
        print(f"✓ Successfully assumed role")

        # Update .env file
        update_env_file(credentials, args.env_file, backup=not args.no_backup)

        print(f"\n✓ Ready to use! Run: uvicorn main:app --reload")

        return 0

    except Exception as e:
        print(f"\n✗ Failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

