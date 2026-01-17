import boto3

ses = boto3.client('ses', region_name='us-east-1')

print("\n" + "="*70)
print("SES CONFIGURATION CHECK")
print("="*70 + "\n")

# Check if in sandbox mode
try:
    account = ses.get_account_sending_enabled()
    print("1. SES Account Status:")
    print(f"   Enabled: {account.get('Enabled', False)}")
    print()
except Exception as e:
    print(f"   Error: {e}\n")

# Check domain verification
try:
    attrs = ses.get_identity_verification_attributes(Identities=['samwylock.com'])
    domain_attrs = attrs['VerificationAttributes'].get('samwylock.com', {})
    print("2. Domain Verification (samwylock.com):")
    print(f"   Status: {domain_attrs.get('VerificationStatus', 'NOT FOUND')}")
    print()
except Exception as e:
    print(f"   Error: {e}\n")

# Check if account is in sandbox
try:
    # Try to get sandbox status - there's no direct API, but we can infer
    print("3. Sandbox Status:")
    print("   Checking by attempting to list sending limits...")

    # Get sending quota
    quota = ses.get_send_quota()
    max_send = quota.get('Max24HourSend', 0)

    if max_send <= 200:
        print(f"   ⚠️  SANDBOX MODE (Max 24hr send: {max_send})")
        print("   In sandbox, can only send TO verified emails")
        print("   Need to request production access")
    else:
        print(f"   ✅ PRODUCTION MODE (Max 24hr send: {max_send})")
    print()
except Exception as e:
    print(f"   Error: {e}\n")

# Check verified identities
try:
    print("4. All Verified Identities:")
    identities = ses.list_identities()
    for identity in identities['Identities']:
        attrs = ses.get_identity_verification_attributes(Identities=[identity])
        status = attrs['VerificationAttributes'].get(identity, {}).get('VerificationStatus', 'Unknown')
        print(f"   - {identity}: {status}")
    print()
except Exception as e:
    print(f"   Error: {e}\n")

print("="*70)
print("DIAGNOSIS")
print("="*70)
print()
print("If you see:")
print("  - Domain Status: Success")
print("  - Sandbox Mode: Yes")
print()
print("Then the issue is:")
print("  You're in SES sandbox mode. In sandbox, you can only send TO")
print("  verified email addresses. The FROM address is fine (domain verified),")
print("  but the TO address must be verified.")
print()
print("Solutions:")
print("  1. Verify the recipient email: sjw787.sw+test@gmail.com")
print("  2. Request production access (recommended)")
print()
print("To verify recipient email:")
print("  aws ses verify-email-identity --email-address sjw787.sw+test@gmail.com")
print()
print("To request production access:")
print("  Go to AWS Console > SES > Account dashboard > Production access")
print()
