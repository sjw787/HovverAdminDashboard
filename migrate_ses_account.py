#!/usr/bin/env python3
"""
Migrate SES configuration from iamadmin-general to iamadmin-dev account.

This script will:
1. Delete the SES domain identity from the current (wrong) account
2. Set up SES in the iamadmin-dev account (052869941234)
3. Preserve DNS records (they're in admin-legacy and don't need to change)
"""
import boto3
import sys
import argparse

TARGET_ACCOUNT = "052869941234"  # iamadmin-dev
DOMAIN = "samwylock.com"
REGION = "us-east-1"


def get_current_account(session):
    """Get current AWS account ID."""
    sts = session.client('sts')
    identity = sts.get_caller_identity()
    return identity['Account'], identity['Arn']


def delete_ses_domain(session, domain):
    """Delete SES domain identity from current account."""
    ses = session.client('ses', region_name=REGION)

    print(f"\n[DELETE] Removing {domain} from current account...")
    try:
        # Check if domain exists
        identities = ses.list_identities()
        if domain in identities['Identities']:
            ses.delete_identity(Identity=domain)
            print(f"[OK] Successfully deleted {domain} from SES")
            return True
        else:
            print(f"[INFO] Domain {domain} not found in this account")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to delete domain: {e}")
        return False


def setup_ses_domain(session, domain):
    """Set up SES domain identity in current account."""
    ses = session.client('ses', region_name=REGION)

    print(f"\n[SETUP] Setting up {domain} in current account...")

    try:
        # Verify domain
        result = ses.verify_domain_identity(Domain=domain)
        verification_token = result['VerificationToken']
        print(f"[OK] Domain verification initiated")
        print(f"   Verification Token: {verification_token}")

        # Enable DKIM
        dkim_result = ses.verify_domain_dkim(Domain=domain)
        dkim_tokens = dkim_result['DkimTokens']
        print(f"[OK] DKIM tokens generated ({len(dkim_tokens)} tokens)")
        for token in dkim_tokens:
            print(f"   - {token}")

        return {
            'verification_token': verification_token,
            'dkim_tokens': dkim_tokens
        }
    except Exception as e:
        print(f"[ERROR] Failed to setup domain: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='Migrate SES from general to dev account')
    parser.add_argument('--delete-only', action='store_true',
                       help='Only delete from current account, do not setup in new account')
    parser.add_argument('--setup-only', action='store_true',
                       help='Only setup in current account, do not delete first')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be done without making changes')
    args = parser.parse_args()

    print("="*70)
    print("SES Account Migration Tool")
    print("="*70)

    # Get current account
    session = boto3.Session()
    account_id, arn = get_current_account(session)

    print(f"\nCurrent Account: {account_id}")
    print(f"User ARN: {arn}")
    print(f"Target Account: {TARGET_ACCOUNT} (iamadmin-dev)")
    print()

    if args.dry_run:
        print("[DRY RUN] No changes will be made\n")

    # Determine what to do
    if account_id == TARGET_ACCOUNT:
        print("[OK] Already in the target account (iamadmin-dev)")
        if not args.delete_only:
            if args.dry_run:
                print("[DRY RUN] Would setup SES domain in this account")
            else:
                result = setup_ses_domain(session, DOMAIN)
                if result:
                    print("\n" + "="*70)
                    print("SUCCESS")
                    print("="*70)
                    print(f"\nSES has been configured in iamadmin-dev ({TARGET_ACCOUNT})")
                    print("DNS records in Route53 (admin-legacy) are already correct.")
                    print(f"\nVerification Token: {result['verification_token']}")
                    print("\nDKIM Tokens:")
                    for token in result['dkim_tokens']:
                        print(f"  - {token}")
                    print("\nWait 5-30 minutes for DNS propagation, then check:")
                    print("  python setup_ses.py --check-status samwylock.com")
    else:
        print(f"[WARNING] Currently in wrong account ({account_id})")
        print(f"          Need to migrate to {TARGET_ACCOUNT} (iamadmin-dev)")
        print()

        if not args.setup_only:
            if args.dry_run:
                print(f"[DRY RUN] Would delete {DOMAIN} from current account")
            else:
                confirm = input(f"Delete {DOMAIN} from account {account_id}? (yes/no): ")
                if confirm.lower() == 'yes':
                    delete_ses_domain(session, DOMAIN)
                else:
                    print("[CANCELLED] No changes made")
                    return

        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print(f"\n1. Switch AWS credentials to iamadmin-dev account ({TARGET_ACCOUNT})")
        print("   You can use environment variables or AWS profile")
        print()
        print("2. Run this script again with --setup-only flag:")
        print(f"   python {sys.argv[0]} --setup-only")
        print()
        print("3. DNS records are already in Route53 (admin-legacy)")
        print("   They will automatically work with the new SES setup")
        print()


if __name__ == "__main__":
    main()
