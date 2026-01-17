#!/usr/bin/env python3
"""
Check which AWS account has SES configured and help migrate to the correct account.
"""
import boto3
import sys

def check_account_ses(profile=None, account_name="default"):
    """Check SES configuration in a specific account."""
    session_kwargs = {}
    if profile:
        session_kwargs['profile_name'] = profile

    try:
        session = boto3.Session(**session_kwargs)
        sts = session.client('sts')
        ses = session.client('ses', region_name='us-east-1')

        # Get account info
        identity = sts.get_caller_identity()
        account_id = identity['Account']
        user_arn = identity['Arn']

        print(f"\n{'='*70}")
        print(f"Account: {account_name}")
        print(f"{'='*70}")
        print(f"Account ID: {account_id}")
        print(f"User ARN: {user_arn}")
        print()

        # Check SES identities
        identities = ses.list_identities()
        if identities['Identities']:
            print(f"SES Identities ({len(identities['Identities'])} found):")
            for identity_name in identities['Identities']:
                print(f"  - {identity_name}")

            # Check if samwylock.com is here
            if 'samwylock.com' in identities['Identities']:
                print()
                print("✅ Domain samwylock.com is configured in this account!")

                # Check verification status
                attrs = ses.get_identity_verification_attributes(Identities=['samwylock.com'])
                domain_attrs = attrs['VerificationAttributes'].get('samwylock.com', {})
                status = domain_attrs.get('VerificationStatus', 'Not Found')
                token = domain_attrs.get('VerificationToken', 'N/A')

                print(f"   Verification Status: {status}")
                print(f"   Verification Token: {token}")

                # Check DKIM
                dkim_attrs = ses.get_identity_dkim_attributes(Identities=['samwylock.com'])
                domain_dkim = dkim_attrs['DkimAttributes'].get('samwylock.com', {})
                dkim_enabled = domain_dkim.get('DkimEnabled', False)
                dkim_status = domain_dkim.get('DkimVerificationStatus', 'N/A')
                dkim_tokens = domain_dkim.get('DkimTokens', [])

                print(f"   DKIM Enabled: {dkim_enabled}")
                print(f"   DKIM Status: {dkim_status}")
                if dkim_tokens:
                    print(f"   DKIM Tokens: {len(dkim_tokens)} tokens")
                    for token in dkim_tokens:
                        print(f"     - {token}")

                return account_id, True
        else:
            print("No SES identities found in this account.")

        return account_id, False

    except Exception as e:
        print(f"\n❌ Error checking account '{account_name}': {e}")
        return None, False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("AWS SES Account Checker")
    print("="*70)

    # Check default profile (likely iamadmin-general based on error)
    default_account, default_has_ses = check_account_ses(profile=None, account_name="Default Profile")

    # Try to check with dev profile if it exists
    # Note: You may need to configure AWS profiles for different accounts

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if default_has_ses:
        print(f"\n⚠️  SES is configured in account: {default_account}")
        print("    This appears to be the iamadmin-general account")
        print()
        print("RECOMMENDATION:")
        print("1. Delete the SES domain identity from iamadmin-general account")
        print("2. Re-run setup_ses.py with credentials for iamadmin-dev (052869941234)")
        print("3. DNS records in Route53 can stay the same (they're in admin-legacy)")
    else:
        print("\n✅ SES domain not found in current account")
        print("   You can proceed to configure SES in the correct account")

    print()
    print("Expected accounts:")
    print("  - iamadmin-dev: 052869941234 (should have SES, Cognito, S3)")
    print("  - admin-legacy: (has Route53 hosted zone)")
    print()
