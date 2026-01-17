import boto3
import json

print("\n" + "="*70)
print("SES VERIFICATION STATUS CHECK")
print("="*70 + "\n")

ses = boto3.client('ses', region_name='us-east-1')
sts = boto3.client('sts')

# Get account
account = sts.get_caller_identity()['Account']
print(f"AWS Account: {account}")

if account == '052869941234':
    print("[OK] Correct account (iamadmin-dev)\n")
else:
    print(f"[WARNING] Account mismatch! Expected 052869941234, got {account}\n")
    print("You need to switch to iamadmin-dev account credentials!\n")

# Check domain verification
print("Domain Verification:")
print("-" * 50)
try:
    attrs = ses.get_identity_verification_attributes(Identities=['samwylock.com'])
    domain_attrs = attrs['VerificationAttributes'].get('samwylock.com', {})

    status = domain_attrs.get('VerificationStatus', 'Not Found')
    token = domain_attrs.get('VerificationToken', 'N/A')

    print(f"Status: {status}")
    print(f"Token: {token}")

    if status == 'Success':
        print("[OK] Domain is VERIFIED\n")
    elif status == 'Pending':
        print("[WAIT] Domain verification PENDING (waiting for DNS)\n")
    else:
        print(f"[ERROR] Domain verification: {status}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

# Check DKIM
print("DKIM Verification:")
print("-" * 50)
try:
    dkim_attrs = ses.get_identity_dkim_attributes(Identities=['samwylock.com'])
    domain_dkim = dkim_attrs['DkimAttributes'].get('samwylock.com', {})

    enabled = domain_dkim.get('DkimEnabled', False)
    dkim_status = domain_dkim.get('DkimVerificationStatus', 'Not Found')
    tokens = domain_dkim.get('DkimTokens', [])

    print(f"Enabled: {enabled}")
    print(f"Status: {dkim_status}")
    print(f"Tokens ({len(tokens)}):")
    for i, token in enumerate(tokens, 1):
        print(f"  {i}. {token}")

    if dkim_status == 'Success':
        print("\n[OK] DKIM is VERIFIED\n")
    elif dkim_status == 'Pending':
        print("\n[WAIT] DKIM verification PENDING (waiting for DNS)\n")
    else:
        print(f"\n[ERROR] DKIM verification: {dkim_status}\n")
except Exception as e:
    print(f"❌ Error: {e}\n")

print("="*70)
print("DNS TIMEOUT EXPLANATION")
print("="*70)
print("\nIf nslookup is timing out from your local machine, this is likely due to:")
print("  - Corporate firewall blocking DNS queries")
print("  - VPN restrictions")
print("  - Local DNS resolver configuration")
print("  - Network security policies")
print("\n[!] THIS IS NORMAL and does NOT affect SES verification!")
print("\nAWS SES verifies DNS records from their infrastructure, not your machine.")
print("As long as the records are in Route53, SES will find them.")
print("\nIf the status above shows 'Success', everything is working correctly!")
print("If the status shows 'Pending', wait 15-30 minutes for DNS propagation.")
print("="*70 + "\n")
