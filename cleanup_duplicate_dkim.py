#!/usr/bin/env python3
"""
Clean up duplicate DKIM records from Route53
"""
import boto3
from botocore.exceptions import ClientError

HOSTED_ZONE_ID = "Z0463989E6ZRMK2X7OOO"
DOMAIN = "samwylock.com"

# Current DKIM tokens from iamadmin-dev SES
CURRENT_DKIM_TOKENS = [
    "kzsrz4en4kwppsab2l5wadcmy7kyio3d",
    "3bniyafthvw7bfx6vaoqltq6jdty5lks",
    "b3j7yyov4iazc3sh2alvzyq7peg5mxfb"
]

# Old DKIM tokens to remove
OLD_DKIM_TOKENS = [
    "3p3rxsm7w2yu6w65stu4nzaw62hgcqpj",
    "lv5mdhfy5b6cjpp3mzrpo7whjhwe5ody",
    "sqlqmdwg5nb3ydif5fdbmf7uhwvcjxve"
]

def get_ses_dkim_tokens():
    """Get current DKIM tokens from SES"""
    ses = boto3.client('ses', region_name='us-east-1')
    try:
        response = ses.get_identity_dkim_attributes(Identities=[DOMAIN])
        dkim_attrs = response['DkimAttributes'].get(DOMAIN, {})
        return dkim_attrs.get('DkimTokens', [])
    except Exception as e:
        print(f"Warning: Could not fetch SES DKIM tokens: {e}")
        return CURRENT_DKIM_TOKENS

def list_dkim_records():
    """List all DKIM records in Route53"""
    session = boto3.Session(profile_name='admin-legacy')
    route53 = session.client('route53')

    try:
        response = route53.list_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID
        )

        dkim_records = []
        for record in response['ResourceRecordSets']:
            if '_domainkey' in record['Name']:
                # Extract token from name
                token = record['Name'].split('._domainkey')[0]
                dkim_records.append({
                    'token': token,
                    'name': record['Name'],
                    'type': record['Type'],
                    'ttl': record.get('TTL', 0),
                    'value': record['ResourceRecords'][0]['Value'] if record.get('ResourceRecords') else None
                })

        return dkim_records
    except Exception as e:
        print(f"Error listing records: {e}")
        return []

def delete_old_dkim_records():
    """Delete old DKIM records"""
    session = boto3.Session(profile_name='admin-legacy')
    route53 = session.client('route53')

    print("\n" + "="*70)
    print("CLEANING UP OLD DKIM RECORDS")
    print("="*70 + "\n")

    # Get current records
    current_records = list_dkim_records()

    print(f"Found {len(current_records)} DKIM records in Route53:\n")

    current_tokens_set = set(CURRENT_DKIM_TOKENS)
    old_tokens_set = set(OLD_DKIM_TOKENS)

    records_to_delete = []

    for record in current_records:
        token = record['token']
        if token in current_tokens_set:
            print(f"✅ KEEP: {token} (current SES token)")
        elif token in old_tokens_set:
            print(f"❌ DELETE: {token} (old token)")
            records_to_delete.append(record)
        else:
            print(f"⚠️  UNKNOWN: {token} (not recognized)")

    if not records_to_delete:
        print("\n✅ No old records to delete. DNS is clean!")
        return True

    print(f"\n{len(records_to_delete)} records will be deleted.\n")

    # Prepare delete changes
    changes = []
    for record in records_to_delete:
        changes.append({
            'Action': 'DELETE',
            'ResourceRecordSet': {
                'Name': record['name'],
                'Type': record['type'],
                'TTL': record['ttl'],
                'ResourceRecords': [{'Value': record['value']}]
            }
        })

    try:
        response = route53.change_resource_record_sets(
            HostedZoneId=HOSTED_ZONE_ID,
            ChangeBatch={
                'Comment': 'Remove old DKIM records from previous SES setup',
                'Changes': changes
            }
        )

        print(f"✅ Successfully deleted {len(records_to_delete)} old DKIM records")
        print(f"Change ID: {response['ChangeInfo']['Id']}")
        print(f"Status: {response['ChangeInfo']['Status']}")
        return True

    except ClientError as e:
        print(f"❌ Error deleting records: {e}")
        return False

def verify_cleanup():
    """Verify that only correct DKIM records remain"""
    print("\n" + "="*70)
    print("VERIFICATION")
    print("="*70 + "\n")

    records = list_dkim_records()
    ses_tokens = get_ses_dkim_tokens()

    print(f"Expected DKIM tokens from SES ({len(ses_tokens)}):")
    for token in ses_tokens:
        print(f"  - {token}")

    print(f"\nDKIM records in Route53 ({len(records)}):")
    for record in records:
        print(f"  - {record['token']}")

    # Check if they match
    route53_tokens = set([r['token'] for r in records])
    ses_tokens_set = set(ses_tokens)

    if route53_tokens == ses_tokens_set and len(records) == 3:
        print("\n✅ PERFECT! Route53 has exactly 3 DKIM records matching SES")
        return True
    elif len(records) > 3:
        print(f"\n❌ ERROR: Too many DKIM records ({len(records)} found, expected 3)")
        extra = route53_tokens - ses_tokens_set
        if extra:
            print(f"Extra tokens in Route53: {extra}")
        return False
    elif len(records) < 3:
        print(f"\n⚠️  WARNING: Not enough DKIM records ({len(records)} found, expected 3)")
        missing = ses_tokens_set - route53_tokens
        if missing:
            print(f"Missing tokens: {missing}")
        return False
    else:
        print("\n⚠️  MISMATCH: Route53 tokens don't match SES tokens")
        print(f"In Route53 but not in SES: {route53_tokens - ses_tokens_set}")
        print(f"In SES but not in Route53: {ses_tokens_set - route53_tokens}")
        return False

if __name__ == "__main__":
    print("\n" + "="*70)
    print("SES DKIM RECORDS CLEANUP TOOL")
    print("="*70)

    # Delete old records
    success = delete_old_dkim_records()

    # Verify cleanup
    verified = verify_cleanup()

    if verified:
        print("\n" + "="*70)
        print("✅ CLEANUP COMPLETE - DNS IS CLEAN")
        print("="*70)
        print("\nNext steps:")
        print("1. Wait 5-10 minutes for DNS propagation")
        print("2. Check SES verification: python setup_ses.py --check-status samwylock.com")
        print("3. Verification should complete successfully now")
    else:
        print("\n" + "="*70)
        print("⚠️  CLEANUP INCOMPLETE")
        print("="*70)
        print("\nPlease review the errors above and run the script again.")

    print()
