#!/usr/bin/env python3
"""
AWS SES Setup Script

This script automates the setup of AWS SES for sending customer emails.
It will:
1. Verify your domain in SES
2. Get DKIM tokens for DNS configuration
3. Optionally verify individual email addresses for testing
4. Request production access (requires manual form submission)
5. Check verification status

Usage:
    python setup_ses.py --domain samwylock.com --region us-east-1
    python setup_ses.py --verify-email test@example.com --region us-east-1
"""

import argparse
import boto3
import json
import sys
from botocore.exceptions import ClientError
from typing import Dict, List


class SESSetup:
    """AWS SES setup automation."""

    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.ses_client = boto3.client('ses', region_name=region)
        print(f"[OK] Connected to AWS SES in region: {region}\n")

    def verify_domain(self, domain: str) -> Dict:
        """
        Verify a domain in SES and get verification token.

        Args:
            domain: Domain name to verify (e.g., samwylock.com)

        Returns:
            Dictionary with verification token
        """
        print(f"[VERIFY] Verifying domain: {domain}")

        try:
            response = self.ses_client.verify_domain_identity(Domain=domain)
            verification_token = response['VerificationToken']

            print(f"[OK] Domain verification initiated!")
            print(f"\n[DNS] Add this TXT record to your DNS:")
            print(f"   Name:  _amazonses.{domain}")
            print(f"   Type:  TXT")
            print(f"   Value: {verification_token}")
            print(f"   TTL:   300 (or default)\n")

            return {
                'domain': domain,
                'verification_token': verification_token,
                'status': 'Pending'
            }
        except ClientError as e:
            print(f"[ERROR] Error verifying domain: {e}")
            sys.exit(1)

    def get_dkim_tokens(self, domain: str) -> List[str]:
        """
        Get DKIM tokens for domain authentication.

        Args:
            domain: Domain name

        Returns:
            List of DKIM tokens
        """
        print(f"[DKIM] Getting DKIM tokens for: {domain}")

        try:
            response = self.ses_client.verify_domain_dkim(Domain=domain)
            dkim_tokens = response['DkimTokens']

            print(f"[OK] DKIM tokens retrieved!")
            print(f"\n[DNS] Add these 3 CNAME records to your DNS:")

            for i, token in enumerate(dkim_tokens, 1):
                print(f"\n   Record {i}:")
                print(f"   Name:  {token}._domainkey.{domain}")
                print(f"   Type:  CNAME")
                print(f"   Value: {token}.dkim.amazonses.com")
                print(f"   TTL:   300 (or default)")

            print()
            return dkim_tokens
        except ClientError as e:
            print(f"[ERROR] Error getting DKIM tokens: {e}")
            return []

    def verify_email(self, email: str) -> bool:
        """
        Verify an individual email address for testing in sandbox.

        Args:
            email: Email address to verify

        Returns:
            True if successful
        """
        print(f"[EMAIL] Verifying email address: {email}")

        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            print(f"[OK] Verification email sent to: {email}")
            print(f"   Please check your inbox and click the verification link.\n")
            return True
        except ClientError as e:
            print(f"[ERROR] Error verifying email: {e}")
            return False

    def check_verification_status(self, identity: str) -> str:
        """
        Check the verification status of a domain or email.

        Args:
            identity: Domain or email to check

        Returns:
            Verification status
        """
        print(f"[CHECK] Checking verification status for: {identity}")

        try:
            response = self.ses_client.get_identity_verification_attributes(
                Identities=[identity]
            )

            if identity in response['VerificationAttributes']:
                status = response['VerificationAttributes'][identity]['VerificationStatus']
                print(f"   Status: {status}")

                if status == 'Success':
                    print(f"   [OK] {identity} is verified and ready to use!")
                elif status == 'Pending':
                    print(f"   [WAIT] {identity} is pending verification.")
                    print(f"   Please add the DNS records and wait 5-30 minutes.")
                else:
                    print(f"   [WARN] {identity} verification status: {status}")

                return status
            else:
                print(f"   [ERROR] {identity} not found in SES.")
                return 'NotFound'
        except ClientError as e:
            print(f"[ERROR] Error checking status: {e}")
            return 'Error'

    def list_verified_identities(self):
        """List all verified identities."""
        print("[LIST] Listing all verified identities:\n")

        try:
            response = self.ses_client.list_verified_email_addresses()
            emails = response.get('VerifiedEmailAddresses', [])

            if emails:
                print("[OK] Verified Email Addresses:")
                for email in emails:
                    print(f"   • {email}")
            else:
                print("   No verified email addresses found.")

            # List domains
            response = self.ses_client.list_identities(IdentityType='Domain')
            domains = response.get('Identities', [])

            if domains:
                print("\n[OK] Verified Domains:")
                for domain in domains:
                    status = self.check_verification_status(domain)
                    if status == 'Success':
                        print(f"   - {domain} [OK]")
                    else:
                        print(f"   - {domain} (Status: {status})")
            else:
                print("\n   No domains found.")

            print()
        except ClientError as e:
            print(f"[ERROR] Error listing identities: {e}")

    def check_sandbox_status(self):
        """Check if SES is in sandbox mode."""
        print("[SANDBOX] Checking SES sandbox status:\n")

        try:
            response = self.ses_client.get_account_sending_enabled()
            enabled = response.get('Enabled', False)

            if enabled:
                print("   [OK] Sending is enabled for your account.")
            else:
                print("   [WARN] Sending is disabled for your account.")

            # Try to get send quota (not available in all regions)
            try:
                quota = self.ses_client.get_send_quota()
                max_24 = quota.get('Max24HourSend', 0)
                max_rate = quota.get('MaxSendRate', 0)
                sent = quota.get('SentLast24Hours', 0)

                print(f"\n[QUOTA] Your SES Sending Limits:")
                print(f"   - Max emails per 24 hours: {max_24:.0f}")
                print(f"   - Max send rate: {max_rate:.0f} emails/second")
                print(f"   - Sent in last 24 hours: {sent:.0f}")

                if max_24 <= 200:
                    print(f"\n   [WARN] Your account appears to be in SANDBOX mode.")
                    print(f"   [INFO] To request production access:")
                    print(f"      1. Go to SES Console → Account dashboard")
                    print(f"      2. Click 'Request production access'")
                    print(f"      3. Fill out the form with your use case")
                else:
                    print(f"\n   [OK] Your account is in PRODUCTION mode.")
            except ClientError:
                print(f"\n   [INFO] Could not retrieve send quota (may not be available in this region).")

            print()
        except ClientError as e:
            print(f"[ERROR] Error checking sandbox status: {e}\n")

    def generate_dns_instructions(self, domain: str, verification_token: str, dkim_tokens: List[str]) -> str:
        """
        Generate formatted DNS instructions.

        Args:
            domain: Domain name
            verification_token: Domain verification token
            dkim_tokens: List of DKIM tokens

        Returns:
            Formatted DNS instructions
        """
        instructions = f"""
================================================================================
                         DNS RECORDS TO ADD                                   
================================================================================

Domain: {domain}

1. DOMAIN VERIFICATION (Required)
   ----------------------------------------------------------------------------
   Type:  TXT
   Name:  _amazonses.{domain}
   Value: {verification_token}
   TTL:   300


2. DKIM RECORDS (Required - Add all 3)
   ----------------------------------------------------------------------------
"""

        for i, token in enumerate(dkim_tokens, 1):
            instructions += f"""
   Record {i}:
   Type:  CNAME
   Name:  {token}._domainkey.{domain}
   Value: {token}.dkim.amazonses.com
   TTL:   300
"""

        instructions += f"""

3. SPF RECORD (Recommended)
   ----------------------------------------------------------------------------
   Type:  TXT
   Name:  {domain}
   Value: v=spf1 include:amazonses.com ~all
   TTL:   300


4. DMARC RECORD (Recommended)
   ----------------------------------------------------------------------------
   Type:  TXT
   Name:  _dmarc.{domain}
   Value: v=DMARC1; p=none; rua=mailto:postmaster@{domain}
   TTL:   300


NOTES:
   - Add all records to your DNS provider (Cloudflare, Route53, etc.)
   - Verification usually takes 5-30 minutes, up to 72 hours
   - You can check status with: python setup_ses.py --check-status {domain}
   - SPF and DMARC improve email deliverability (highly recommended)

"""
        return instructions


def main():
    parser = argparse.ArgumentParser(
        description='AWS SES Setup Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Verify domain and get DNS records
  python setup_ses.py --domain samwylock.com
  
  # Verify email for testing
  python setup_ses.py --verify-email test@example.com
  
  # Check verification status
  python setup_ses.py --check-status samwylock.com
  
  # List all verified identities
  python setup_ses.py --list
  
  # Check sandbox status
  python setup_ses.py --sandbox-status
        """
    )

    parser.add_argument('--domain', type=str,
                        help='Domain to verify (e.g., samwylock.com)')
    parser.add_argument('--verify-email', type=str,
                        help='Email address to verify for testing')
    parser.add_argument('--check-status', type=str,
                        help='Check verification status of domain or email')
    parser.add_argument('--list', action='store_true',
                        help='List all verified identities')
    parser.add_argument('--sandbox-status', action='store_true',
                        help='Check SES sandbox status')
    parser.add_argument('--region', type=str, default='us-east-1',
                        help='AWS region (default: us-east-1)')
    parser.add_argument('--output-dns', type=str,
                        help='Save DNS instructions to file')

    args = parser.parse_args()

    # Initialize SES setup
    ses_setup = SESSetup(region=args.region)

    # Execute requested action
    if args.domain:
        # Verify domain and get DKIM
        result = ses_setup.verify_domain(args.domain)
        dkim_tokens = ses_setup.get_dkim_tokens(args.domain)

        # Generate DNS instructions
        dns_instructions = ses_setup.generate_dns_instructions(
            args.domain,
            result['verification_token'],
            dkim_tokens
        )

        print(dns_instructions)

        # Save to file if requested
        if args.output_dns:
            with open(args.output_dns, 'w') as f:
                f.write(dns_instructions)
            print(f"[OK] DNS instructions saved to: {args.output_dns}\n")
        else:
            # Offer to save
            save = input("Save DNS instructions to file? (y/n): ").lower()
            if save == 'y':
                filename = f"ses_dns_records_{args.domain.replace('.', '_')}.txt"
                with open(filename, 'w') as f:
                    f.write(dns_instructions)
                print(f"[OK] DNS instructions saved to: {filename}\n")

    elif args.verify_email:
        ses_setup.verify_email(args.verify_email)

    elif args.check_status:
        ses_setup.check_verification_status(args.check_status)
        print()

    elif args.list:
        ses_setup.list_verified_identities()

    elif args.sandbox_status:
        ses_setup.check_sandbox_status()

    else:
        parser.print_help()
        print("\n[TIP] Start with: python setup_ses.py --domain samwylock.com\n")


if __name__ == '__main__':
    main()
