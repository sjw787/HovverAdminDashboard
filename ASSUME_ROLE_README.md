# AWS Assume Role Script

This script generates temporary AWS access keys by assuming an IAM role using AWS STS (Security Token Service).

## Prerequisites

1. AWS credentials configured (via environment variables, AWS CLI, or IAM role)
2. Python 3.14+ with boto3 installed
3. Permissions to assume the target role

## Installation

The required dependencies are already in `pyproject.toml`. If you need to install them separately:

```powershell
pip install boto3
```

## Basic Usage

```powershell
python assume_role.py arn:aws:iam::123456789012:role/MyRole
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `role_arn` | (Required) ARN of the IAM role to assume |
| `--session-name` | Name for the assumed role session (default: auto-generated) |
| `--duration` | Duration in seconds (900-43200, default: 3600) |
| `--region` | AWS region (default: from AWS_REGION or us-east-1) |
| `--external-id` | External ID for cross-account access |
| `--mfa-serial` | MFA device serial number |
| `--mfa-token` | Current MFA token code (6 digits) |
| `--format` | Output format: text, json, env, export, powershell |
| `--save-to-file` | Save credentials to a file |

## Examples

### 1. Basic Role Assumption

```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole
```

### 2. Custom Duration (2 hours)

```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --duration 7200
```

### 3. Cross-Account Access with External ID

```powershell
python assume_role.py arn:aws:iam::987654321098:role/CrossAccountRole --external-id my-external-id-123
```

### 4. With MFA Authentication

```powershell
python assume_role.py arn:aws:iam::123456789012:role/SecureRole `
  --mfa-serial arn:aws:iam::123456789012:mfa/john.doe `
  --mfa-token 123456
```

### 5. Output as PowerShell Commands

```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --format powershell
```

Output:
```powershell
$env:AWS_ACCESS_KEY_ID='ASIA...'
$env:AWS_SECRET_ACCESS_KEY='...'
$env:AWS_SESSION_TOKEN='...'
# Expires at: 2026-01-14T15:30:00+00:00
```

To use these credentials in your current PowerShell session:
```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --format powershell | Invoke-Expression
```

### 6. Output as JSON

```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --format json
```

### 7. Save to Environment File

```powershell
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --save-to-file .env.assumed
```

This creates a `.env.assumed` file that you can load into your application.

### 8. For Unix/Linux (export commands)

```bash
python assume_role.py arn:aws:iam::123456789012:role/AdminRole --format export
```

Then source it:
```bash
eval $(python assume_role.py arn:aws:iam::123456789012:role/AdminRole --format export)
```

## Output Formats

### text (default)
Human-readable format with all credential details

### json
Machine-readable JSON format for programmatic use

### env
Environment variable format (Windows-style)
```
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
```

### export
Unix-style export commands
```bash
export AWS_ACCESS_KEY_ID=ASIA...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...
```

### powershell
PowerShell environment variable commands
```powershell
$env:AWS_ACCESS_KEY_ID='ASIA...'
$env:AWS_SECRET_ACCESS_KEY='...'
$env:AWS_SESSION_TOKEN='...'
```

## IAM Role Trust Policy

For the script to work, the IAM role must have a trust policy that allows your AWS identity to assume it:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:user/your-user"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "optional-external-id"
        }
      }
    }
  ]
}
```

For MFA requirement:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::123456789012:user/your-user"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "Bool": {
          "aws:MultiFactorAuthPresent": "true"
        }
      }
    }
  ]
}
```

## IAM Permissions Required

Your AWS identity needs the following permission:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::*:role/YourRoleName"
    }
  ]
}
```

## Use Cases

1. **Development Environment**: Assume different roles for testing various permission levels
2. **Cross-Account Access**: Access resources in different AWS accounts
3. **CI/CD Pipelines**: Generate temporary credentials for deployment scripts
4. **Security**: Use temporary credentials instead of long-term access keys
5. **Role Switching**: Switch between different roles for different tasks

## Security Best Practices

1. **Use Short Durations**: Request only the duration you need (minimum 15 minutes)
2. **Enable MFA**: Use MFA when assuming sensitive roles
3. **External IDs**: Use external IDs for cross-account access
4. **Least Privilege**: Only assume roles with permissions you need
5. **Rotate Regularly**: Generate new temporary credentials when old ones expire
6. **Don't Commit Credentials**: Add `.env.assumed` to `.gitignore`

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

Your AWS identity doesn't have permission to assume the role. Check:
- Your IAM user/role has `sts:AssumeRole` permission
- The target role's trust policy includes your identity

### Error: "Access denied"

The role's trust policy might require:
- External ID (use `--external-id`)
- MFA (use `--mfa-serial` and `--mfa-token`)
- Specific conditions (check the role's trust policy)

### Error: "No credentials found"

Configure AWS credentials using one of:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- AWS CLI (`aws configure`)
- IAM role (when running on EC2/ECS/Lambda)

### Expired Credentials

Temporary credentials expire after the specified duration. Generate new ones when needed.

## Integration with Hovver Admin Dashboard

To use assumed role credentials with the dashboard:

```powershell
# Generate credentials
python assume_role.py arn:aws:iam::123456789012:role/HovverAdminRole --save-to-file .env.assumed

# Update your .env file or load the assumed credentials
# Then run the application
uvicorn main:app --reload
```

Or use them directly in PowerShell:
```powershell
# Assume role and set environment variables
python assume_role.py arn:aws:iam::123456789012:role/HovverAdminRole --format powershell | Invoke-Expression

# Run the application with temporary credentials
uvicorn main:app --reload
```

## Additional Resources

- [AWS STS Documentation](https://docs.aws.amazon.com/STS/latest/APIReference/welcome.html)
- [IAM Roles](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [Temporary Security Credentials](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html)

