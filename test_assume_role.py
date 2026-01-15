"""
Unit tests for assume_role.py
These tests validate the script logic without making actual AWS API calls.
"""
import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from assume_role import RoleAssumer


class TestRoleAssumer(unittest.TestCase):
    """Test cases for RoleAssumer class."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_role_arn = "arn:aws:iam::123456789012:role/TestRole"
        self.test_region = "us-east-1"

    def test_initialization_defaults(self):
        """Test RoleAssumer initialization with defaults."""
        assumer = RoleAssumer(role_arn=self.test_role_arn)

        self.assertEqual(assumer.role_arn, self.test_role_arn)
        self.assertEqual(assumer.duration_seconds, 3600)
        self.assertIsNotNone(assumer.session_name)
        self.assertTrue(assumer.session_name.startswith("AssumeRoleSession-"))

    def test_initialization_custom_values(self):
        """Test RoleAssumer initialization with custom values."""
        session_name = "MyCustomSession"
        duration = 7200
        external_id = "my-external-id"

        assumer = RoleAssumer(
            role_arn=self.test_role_arn,
            session_name=session_name,
            duration_seconds=duration,
            region=self.test_region,
            external_id=external_id
        )

        self.assertEqual(assumer.role_arn, self.test_role_arn)
        self.assertEqual(assumer.session_name, session_name)
        self.assertEqual(assumer.duration_seconds, duration)
        self.assertEqual(assumer.region, self.test_region)
        self.assertEqual(assumer.external_id, external_id)

    def test_duration_clamping(self):
        """Test that duration is clamped to valid range."""
        # Test minimum clamping
        assumer_min = RoleAssumer(
            role_arn=self.test_role_arn,
            duration_seconds=100  # Too short
        )
        self.assertEqual(assumer_min.duration_seconds, 900)

        # Test maximum clamping
        assumer_max = RoleAssumer(
            role_arn=self.test_role_arn,
            duration_seconds=999999  # Too long
        )
        self.assertEqual(assumer_max.duration_seconds, 43200)

    @patch('assume_role.boto3.client')
    def test_assume_role_basic(self, mock_boto_client):
        """Test basic role assumption."""
        # Mock the STS client and response
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts

        mock_credentials = {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "AQoDYXdzEJr...",
            "Expiration": datetime.now(timezone.utc)
        }

        mock_response = {
            "Credentials": mock_credentials,
            "AssumedRoleUser": {
                "Arn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
                "AssumedRoleId": "AROA3XFRBF535PLBIFPI4:session"
            }
        }

        mock_sts.assume_role.return_value = mock_response

        # Create assumer and call assume_role
        assumer = RoleAssumer(role_arn=self.test_role_arn)
        result = assumer.assume_role()

        # Verify the STS client was called correctly
        mock_sts.assume_role.assert_called_once()
        call_args = mock_sts.assume_role.call_args[1]
        self.assertEqual(call_args["RoleArn"], self.test_role_arn)
        self.assertEqual(call_args["DurationSeconds"], 3600)

        # Verify the returned credentials
        self.assertEqual(result["AccessKeyId"], mock_credentials["AccessKeyId"])
        self.assertEqual(result["SecretAccessKey"], mock_credentials["SecretAccessKey"])
        self.assertEqual(result["SessionToken"], mock_credentials["SessionToken"])

    @patch('assume_role.boto3.client')
    def test_assume_role_with_external_id(self, mock_boto_client):
        """Test role assumption with external ID."""
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts

        mock_credentials = {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "AQoDYXdzEJr...",
            "Expiration": datetime.now(timezone.utc)
        }

        mock_response = {
            "Credentials": mock_credentials,
            "AssumedRoleUser": {
                "Arn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
                "AssumedRoleId": "AROA3XFRBF535PLBIFPI4:session"
            }
        }

        mock_sts.assume_role.return_value = mock_response

        # Create assumer with external ID
        external_id = "my-external-id-123"
        assumer = RoleAssumer(
            role_arn=self.test_role_arn,
            external_id=external_id
        )
        assumer.assume_role()

        # Verify external ID was passed
        call_args = mock_sts.assume_role.call_args[1]
        self.assertEqual(call_args["ExternalId"], external_id)

    @patch('assume_role.boto3.client')
    def test_assume_role_with_mfa(self, mock_boto_client):
        """Test role assumption with MFA."""
        mock_sts = Mock()
        mock_boto_client.return_value = mock_sts

        mock_credentials = {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "SessionToken": "AQoDYXdzEJr...",
            "Expiration": datetime.now(timezone.utc)
        }

        mock_response = {
            "Credentials": mock_credentials,
            "AssumedRoleUser": {
                "Arn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
                "AssumedRoleId": "AROA3XFRBF535PLBIFPI4:session"
            }
        }

        mock_sts.assume_role.return_value = mock_response

        # Create assumer with MFA
        mfa_serial = "arn:aws:iam::123456789012:mfa/user"
        mfa_token = "123456"
        assumer = RoleAssumer(
            role_arn=self.test_role_arn,
            mfa_serial=mfa_serial,
            mfa_token=mfa_token
        )
        assumer.assume_role()

        # Verify MFA parameters were passed
        call_args = mock_sts.assume_role.call_args[1]
        self.assertEqual(call_args["SerialNumber"], mfa_serial)
        self.assertEqual(call_args["TokenCode"], mfa_token)

    def test_print_credentials_formats(self):
        """Test different credential output formats."""
        credentials = {
            "AccessKeyId": "ASIAIOSFODNN7EXAMPLE",
            "SecretAccessKey": "secret123",
            "SessionToken": "token123",
            "Expiration": "2026-01-14T15:00:00+00:00",
            "AssumedRoleArn": "arn:aws:sts::123456789012:assumed-role/TestRole/session",
            "AssumedRoleId": "AROA123:session"
        }

        assumer = RoleAssumer(role_arn=self.test_role_arn)

        # Test different formats don't raise exceptions
        import io
        import sys

        for format_type in ["text", "json", "env", "export", "powershell"]:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                assumer.print_credentials(credentials, format=format_type)
                output = sys.stdout.getvalue()
                self.assertIsInstance(output, str)
                self.assertGreater(len(output), 0)
            finally:
                sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()

