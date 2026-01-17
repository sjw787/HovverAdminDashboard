import boto3
import json

print("\n" + "="*70)
print("WELCOME EMAIL STATUS CHECK")
print("="*70 + "\n")

# 1. Check SES
print("1. SES Domain Verification:")
ses = boto3.client('ses', region_name='us-east-1')
attrs = ses.get_identity_verification_attributes(Identities=['samwylock.com'])
domain_status = attrs['VerificationAttributes'].get('samwylock.com', {}).get('VerificationStatus', 'Not Found')
dkim_attrs = ses.get_identity_dkim_attributes(Identities=['samwylock.com'])
dkim_status = dkim_attrs['DkimAttributes'].get('samwylock.com', {}).get('DkimVerificationStatus', 'Not Found')

print(f"   Domain: {domain_status}")
print(f"   DKIM: {dkim_status}")

if domain_status == 'Success' and dkim_status == 'Success':
    print("   ✅ SES is ready\n")
else:
    print("   ❌ SES not verified yet\n")

# 2. Check Cognito
print("2. Cognito Email Configuration:")
cognito = boto3.client('cognito-idp', region_name='us-east-1')
pool = cognito.describe_user_pool(UserPoolId='us-east-1_vqzmBxIoP')
email_config = pool['UserPool'].get('EmailConfiguration', {})
sending_account = email_config.get('EmailSendingAccount', 'COGNITO_DEFAULT')
from_email = email_config.get('From', 'Not set')
source_arn = email_config.get('SourceArn', 'Not set')

print(f"   Sending Account: {sending_account}")
print(f"   FROM Email: {from_email}")
print(f"   Source ARN: {source_arn}")

if sending_account == 'DEVELOPER' and '052869941234' in source_arn:
    print("   ✅ Cognito configured to use SES\n")
else:
    print("   ❌ Cognito NOT configured for SES\n")
    print("   Run: python configure_cognito_ses.py\n")

# 3. Summary
print("="*70)
if domain_status == 'Success' and dkim_status == 'Success' and sending_account == 'DEVELOPER':
    print("✅ ALL SYSTEMS GO!")
    print("\nWelcome emails are ready to send!")
    print("Create a customer to test: POST /customers")
else:
    print("⚠️  SETUP INCOMPLETE")
    if domain_status != 'Success' or dkim_status != 'Success':
        print("   - Wait for SES verification (5-30 min)")
    if sending_account != 'DEVELOPER':
        print("   - Configure Cognito: python configure_cognito_ses.py")
print("="*70 + "\n")
