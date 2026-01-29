"""
Lambda handler for AWS Lambda deployment.
Uses Mangum to adapt FastAPI to AWS Lambda's event format.
"""
import os
import json
import boto3


# Remove any AWS credential environment variables to force boto3 to use IAM role
# Lambda provides credentials via the execution role, not environment variables
for env_var in ['AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN']:
    if env_var in os.environ and not os.environ[env_var]:
        # Remove empty credential environment variables
        print(f"Removing empty {env_var} environment variable")
        del os.environ[env_var]


def get_secret(secret_name: str) -> str:
    """
    Retrieve secret from AWS Secrets Manager.
    Used to fetch RESEND_API_KEY at Lambda cold start.
    """
    region = os.environ.get('AWS_REGION', 'us-east-1')
    client = boto3.client('secretsmanager', region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        if 'SecretString' in response:
            return response['SecretString']
        else:
            # Binary secret (shouldn't happen for API keys)
            import base64
            return base64.b64decode(response['SecretBinary']).decode('utf-8')
    except Exception as e:
        print(f"Error fetching secret {secret_name}: {e}")
        raise


# Initialize secrets at cold start BEFORE importing app
if 'RESEND_API_KEY_SECRET' in os.environ and 'RESEND_API_KEY' not in os.environ:
    secret_name = os.environ['RESEND_API_KEY_SECRET']
    print(f"Fetching secret: {secret_name}")
    os.environ['RESEND_API_KEY'] = get_secret(secret_name)
    print("Secret loaded successfully")


# Now import the app after setting up environment
from mangum import Mangum
from main import app


# Lambda handler - Mangum adapter wraps FastAPI app
# This makes FastAPI compatible with AWS Lambda/ALB events
handler = Mangum(app, lifespan="off")

