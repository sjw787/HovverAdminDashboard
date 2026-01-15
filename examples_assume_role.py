"""
Example usage script for assume_role.py
Demonstrates various ways to use the role assumption script.
"""

# Example 1: Basic usage with text output
print("Example 1: Basic role assumption")
print("=" * 80)
print("Command:")
print("  python assume_role.py arn:aws:iam::123456789012:role/MyRole")
print("\nThis will display temporary credentials in human-readable format.")
print()

# Example 2: PowerShell environment variables
print("Example 2: Set environment variables in PowerShell")
print("=" * 80)
print("Command:")
print("  python assume_role.py arn:aws:iam::123456789012:role/MyRole --format powershell | Invoke-Expression")
print("\nThis will set the temporary credentials as environment variables in your current PowerShell session.")
print()

# Example 3: Save to file
print("Example 3: Save credentials to file")
print("=" * 80)
print("Command:")
print("  python assume_role.py arn:aws:iam::123456789012:role/MyRole --save-to-file .env.assumed")
print("\nThis will save the credentials to .env.assumed file.")
print()

# Example 4: With MFA
print("Example 4: Assume role with MFA")
print("=" * 80)
print("Command:")
print("""  python assume_role.py arn:aws:iam::123456789012:role/SecureRole `
    --mfa-serial arn:aws:iam::123456789012:mfa/user `
    --mfa-token 123456""")
print("\nThis will assume the role using MFA authentication.")
print()

# Example 5: Cross-account with external ID
print("Example 5: Cross-account access with external ID")
print("=" * 80)
print("Command:")
print("""  python assume_role.py arn:aws:iam::987654321098:role/CrossAccountRole `
    --external-id my-external-id-123 `
    --duration 7200""")
print("\nThis will assume a role in another AWS account with a 2-hour duration.")
print()

# Example 6: JSON output for scripting
print("Example 6: JSON output for programmatic use")
print("=" * 80)
print("Command:")
print("  python assume_role.py arn:aws:iam::123456789012:role/MyRole --format json")
print("\nThis will output credentials in JSON format for parsing by other scripts.")
print()

# Example 7: Integration with the dashboard
print("Example 7: Use with Hovver Admin Dashboard")
print("=" * 80)
print("Commands:")
print("""  # Generate and load credentials
  python assume_role.py arn:aws:iam::123456789012:role/HovverAdminRole --format powershell | Invoke-Expression
  
  # Run the dashboard
  uvicorn main:app --reload""")
print("\nThis will run the dashboard with temporary credentials from the assumed role.")
print()

print("\nFor more information, see ASSUME_ROLE_README.md")

