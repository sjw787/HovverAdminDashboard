"""
Authentication service using AWS Cognito.
"""
from typing import Dict, Any, List
import secrets
import string

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import requests

from config import settings
from api.services.email import email_service


# HTTP Bearer token scheme
security = HTTPBearer()


class CognitoAuth:
    """AWS Cognito authentication service."""

    def __init__(self):
        self.user_pool_id = settings.cognito_user_pool_id
        self.client_id = settings.cognito_client_id
        self.region = settings.effective_cognito_region

        # Initialize Cognito client
        # Only use explicit credentials if both are provided and non-empty
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            self.client = boto3.client(
                'cognito-idp',
                region_name=self.region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key
            )
        else:
            # Use IAM role credentials (for ECS tasks) or default credential chain
            self.client = boto3.client('cognito-idp', region_name=self.region)

        # Cache for JWKS keys
        self._jwks: Dict[str, Any] | None = None

    def _generate_temporary_password(self) -> str:
        """
        Generate a secure temporary password that meets Cognito requirements.

        Requirements:
        - Minimum 8 characters
        - At least 1 uppercase letter
        - At least 1 lowercase letter
        - At least 1 number
        - At least 1 special character

        Returns:
            A secure random password string
        """
        # Define character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special = "!@#$%^&*"

        # Ensure at least one character from each required set
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special),
        ]

        # Fill the rest with random characters from all sets
        all_chars = uppercase + lowercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(12))  # Total 16 chars

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    def _get_jwks(self) -> Dict[str, Any]:
        """Get JSON Web Key Set from Cognito."""
        if self._jwks is None:
            jwks_url = f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}/.well-known/jwks.json"
            response = requests.get(jwks_url)
            response.raise_for_status()
            self._jwks = response.json()
        return self._jwks

    def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with Cognito.

        Args:
            username: User's username
            password: User's password

        Returns:
            Dictionary containing authentication tokens

        Raises:
            HTTPException: If authentication fails
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )

            # Check if we have an authentication challenge
            if 'ChallengeName' in response:
                challenge_name = response['ChallengeName']
                if challenge_name == 'NEW_PASSWORD_REQUIRED':
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="New password required. Please reset your password."
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Authentication challenge required: {challenge_name}"
                    )

            # Check if we have authentication result
            if 'AuthenticationResult' not in response:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Unexpected response from Cognito: {list(response.keys())}"
                )

            return {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "refresh_token": response['AuthenticationResult']['RefreshToken'],
                "token_type": "Bearer",
                "expires_in": response['AuthenticationResult']['ExpiresIn']
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect username or password"
                )
            elif error_code == 'UserNotFoundException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            elif error_code == 'UserNotConfirmedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User account not confirmed"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Authentication error: {str(e)}"
                )

    def verify_token(self, token: str) -> Dict[str, Any]:
        """
        Verify JWT token from Cognito.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token claims

        Raises:
            HTTPException: If token is invalid
        """
        try:
            # Get the key id from the token header
            headers = jwt.get_unverified_headers(token)
            kid = headers['kid']

            # Find the matching key from JWKS
            jwks = self._get_jwks()
            key = None
            for jwk_key in jwks['keys']:
                if jwk_key['kid'] == kid:
                    key = jwk_key
                    break

            if not key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token key"
                )

            # Verify and decode the token
            public_key = jwk.construct(key)
            message, encoded_signature = token.rsplit('.', 1)
            decoded_signature = base64url_decode(encoded_signature.encode())

            if not public_key.verify(message.encode(), decoded_signature):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token signature"
                )

            # Decode token claims
            claims = jwt.decode(
                token,
                key,
                algorithms=['RS256'],
                audience=self.client_id,
                options={"verify_exp": True}
            )

            return claims

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token verification failed: {str(e)}"
            )

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """
        Get user information from Cognito.

        Args:
            access_token: User's access token

        Returns:
            User information dictionary
        """
        try:
            response = self.client.get_user(AccessToken=access_token)

            user_info = {
                "username": response['Username'],
                "attributes": {}
            }

            for attr in response['UserAttributes']:
                user_info["attributes"][attr['Name']] = attr['Value']

            return user_info

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Failed to get user info: {str(e)}"
            )

    def change_password(self, access_token: str, old_password: str, new_password: str) -> Dict[str, str]:
        """
        Change user's password.

        Args:
            access_token: User's access token
            old_password: Current password
            new_password: New password

        Returns:
            Success message

        Raises:
            HTTPException: If password change fails
        """
        try:
            self.client.change_password(
                AccessToken=access_token,
                PreviousPassword=old_password,
                ProposedPassword=new_password
            )

            return {"message": "Password changed successfully"}

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Current password is incorrect"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password does not meet requirements"
                )
            elif error_code == 'LimitExceededException':
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again later"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to change password: {str(e)}"
                )

    def forgot_password(self, username: str) -> Dict[str, str]:
        """
        Initiate forgot password flow.

        Args:
            username: User's username/email

        Returns:
            Success message with delivery info

        Raises:
            HTTPException: If forgot password fails
        """
        try:
            response = self.client.forgot_password(
                ClientId=self.client_id,
                Username=username
            )

            delivery = response.get('CodeDeliveryDetails', {})
            destination = delivery.get('Destination', 'your email')

            return {
                "message": f"Password reset code sent to {destination}",
                "delivery_medium": delivery.get('DeliveryMedium', 'EMAIL')
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'UserNotFoundException':
                # Don't reveal if user exists for security
                return {
                    "message": "If the email exists, a reset code has been sent",
                    "delivery_medium": "EMAIL"
                }
            elif error_code == 'LimitExceededException':
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again later"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid email address"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to initiate password reset: {str(e)}"
                )

    def confirm_forgot_password(self, username: str, confirmation_code: str, new_password: str) -> Dict[str, str]:
        """
        Confirm forgot password with code.

        Args:
            username: User's username/email
            confirmation_code: Code from email
            new_password: New password

        Returns:
            Success message

        Raises:
            HTTPException: If confirmation fails
        """
        try:
            self.client.confirm_forgot_password(
                ClientId=self.client_id,
                Username=username,
                ConfirmationCode=confirmation_code,
                Password=new_password
            )

            return {"message": "Password reset successfully"}

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'CodeMismatchException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid confirmation code"
                )
            elif error_code == 'ExpiredCodeException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Confirmation code has expired"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password does not meet requirements"
                )
            elif error_code == 'LimitExceededException':
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again later"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to reset password: {str(e)}"
                )

    def update_user_attributes(self, access_token: str, attributes: Dict[str, str]) -> Dict[str, str]:
        """
        Update user attributes.

        Args:
            access_token: User's access token
            attributes: Dictionary of attributes to update

        Returns:
            Success message

        Raises:
            HTTPException: If update fails
        """
        try:
            # Convert dict to list of Name/Value pairs
            user_attributes = [
                {"Name": name, "Value": value}
                for name, value in attributes.items()
                if value is not None
            ]

            if not user_attributes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No attributes provided to update"
                )

            response = self.client.update_user_attributes(
                AccessToken=access_token,
                UserAttributes=user_attributes
            )

            # Check if verification is needed
            code_delivery = response.get('CodeDeliveryDetailsList', [])
            if code_delivery:
                return {
                    "message": "Attributes updated. Verification code sent for new email.",
                    "verification_required": True
                }

            return {"message": "User attributes updated successfully"}

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authorized to update attributes"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid attribute value"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update attributes: {str(e)}"
                )

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: Refresh token from login

        Returns:
            New access and ID tokens

        Raises:
            HTTPException: If refresh fails
        """
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )

            return {
                "access_token": response['AuthenticationResult']['AccessToken'],
                "id_token": response['AuthenticationResult']['IdToken'],
                "token_type": "Bearer",
                "expires_in": response['AuthenticationResult']['ExpiresIn']
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token is invalid or expired"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to refresh token: {str(e)}"
                )

    def complete_new_password_challenge(self, username: str, temporary_password: str, new_password: str) -> Dict[str, Any]:
        """
        Complete NEW_PASSWORD_REQUIRED challenge.

        When an admin creates a user or resets their password, the user must
        complete this challenge on first login with their temporary password.

        Args:
            username: User's username/email
            temporary_password: Temporary password from admin
            new_password: New permanent password to set

        Returns:
            Dictionary containing authentication tokens

        Raises:
            HTTPException: If challenge completion fails
        """
        try:
            # First, initiate auth with temporary password
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': temporary_password
                }
            )

            # Check if we have the NEW_PASSWORD_REQUIRED challenge
            if 'ChallengeName' in response and response['ChallengeName'] == 'NEW_PASSWORD_REQUIRED':
                # Respond to the challenge with new password
                challenge_response = self.client.respond_to_auth_challenge(
                    ClientId=self.client_id,
                    ChallengeName='NEW_PASSWORD_REQUIRED',
                    Session=response['Session'],
                    ChallengeResponses={
                        'USERNAME': username,
                        'NEW_PASSWORD': new_password
                    }
                )

                # Return the authentication tokens
                return {
                    "access_token": challenge_response['AuthenticationResult']['AccessToken'],
                    "id_token": challenge_response['AuthenticationResult']['IdToken'],
                    "refresh_token": challenge_response['AuthenticationResult']['RefreshToken'],
                    "token_type": "Bearer",
                    "expires_in": challenge_response['AuthenticationResult']['ExpiresIn']
                }

            # If no challenge, temporary password was already changed or is incorrect
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No password reset required or temporary password is incorrect"
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NotAuthorizedException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect temporary password"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="New password does not meet requirements"
                )
            elif error_code == 'UserNotFoundException':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            elif error_code == 'LimitExceededException':
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many attempts. Please try again later"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to complete password challenge: {str(e)}"
                )

    def create_customer(
        self,
        email: str,
        name: str,
        phone_number: str | None = None
    ) -> Dict[str, Any]:
        """
        Create a new customer user in Cognito.

        Args:
            email: Customer's email address (required)
            name: Customer's full name
            phone_number: Optional phone number in E.164 format (+1234567890)

        Returns:
            Dictionary with customer details including auto-generated temporary password

        Raises:
            HTTPException: If creation fails
        """
        try:
            # Auto-generate a secure temporary password
            temporary_password = self._generate_temporary_password()

            # Validate phone number format if provided
            if phone_number:
                phone_number = phone_number.strip()
                if not phone_number.startswith('+'):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number must be in E.164 format (e.g., +1234567890)"
                    )
                # Basic validation for E.164 format
                if not phone_number[1:].isdigit() or len(phone_number) < 8 or len(phone_number) > 16:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid phone number format. Must be E.164 format with country code (e.g., +1234567890)"
                    )

            # Prepare user attributes
            user_attributes = [
                {"Name": "email", "Value": email},
                {"Name": "email_verified", "Value": "true"},
                {"Name": "name", "Value": name}
            ]

            if phone_number:
                user_attributes.extend([
                    {"Name": "phone_number", "Value": phone_number},
                    {"Name": "phone_number_verified", "Value": "true"}
                ])

            # Create user
            response = self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=user_attributes,
                TemporaryPassword=temporary_password,
                MessageAction='SUPPRESS'  # Don't send Cognito email - we'll use SES
            )

            user = response['User']
            customer_id = next(
                (attr['Value'] for attr in user['Attributes'] if attr['Name'] == 'sub'),
                None
            )

            # Set the customer_id custom attribute to match the sub
            self.client.admin_update_user_attributes(
                UserPoolId=self.user_pool_id,
                Username=email,
                UserAttributes=[
                    {"Name": "custom:customer_id", "Value": customer_id}
                ]
            )

            # Set password as permanent
            self.client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=email,
                Password=temporary_password,
                Permanent=False  # User must change on first login
            )

            # Add user to Customers group
            self.client.admin_add_user_to_group(
                UserPoolId=self.user_pool_id,
                Username=email,
                GroupName='Customers'
            )

            # Send welcome email via SES
            try:
                email_service.send_welcome_email(
                    recipient_email=email,
                    recipient_name=name,
                    temporary_password=temporary_password
                )
            except Exception as email_error:
                # Log error but don't fail the entire operation
                # Customer was created successfully, just email failed
                print(f"Warning: Failed to send welcome email: {email_error}")
                # Could add to a retry queue here

            return {
                "customer_id": customer_id,
                "email": email,
                "name": name,
                "phone_number": phone_number,
                "customer_folder": f"customers/{customer_id}",
                "created_date": user['UserCreateDate'].isoformat(),
                "enabled": user['Enabled'],
                "user_status": user.get('UserStatus', 'FORCE_CHANGE_PASSWORD'),
                "temporary_password": temporary_password  # Include the generated password
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error'].get('Message', str(e))

            if error_code == 'UsernameExistsException':
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists"
                )
            elif error_code == 'InvalidPasswordException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Password does not meet requirements: {error_message}"
                )
            elif error_code == 'InvalidParameterException':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid parameter: {error_message}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to create customer: {error_message}"
                )

    def list_customers(self, limit: int = 60) -> List[Dict[str, Any]]:
        """
        List all customer users in the Customers group.

        Args:
            limit: Maximum number of users to return

        Returns:
            List of customer profiles

        Raises:
            HTTPException: If listing fails
        """
        try:
            response = self.client.list_users_in_group(
                UserPoolId=self.user_pool_id,
                GroupName='Customers',
                Limit=limit
            )

            customers = []
            for user in response.get('Users', []):
                attributes = {attr['Name']: attr['Value'] for attr in user['Attributes']}

                customer_id = attributes.get('sub')
                customers.append({
                    "customer_id": customer_id,
                    "email": attributes.get('email'),
                    "name": attributes.get('name', ''),
                    "phone_number": attributes.get('phone_number'),
                    "customer_folder": f"customers/{customer_id}",
                    "created_date": user['UserCreateDate'].isoformat(),
                    "enabled": user['Enabled'],
                    "user_status": user.get('UserStatus', 'UNKNOWN')
                })

            return customers

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list customers: {str(e)}"
            )

    def get_customer(self, customer_id: str) -> Dict[str, Any]:
        """
        Get a specific customer by their customer_id (sub).

        Args:
            customer_id: Customer's unique ID

        Returns:
            Customer profile

        Raises:
            HTTPException: If customer not found or retrieval fails
        """
        try:
            # List all customers and find the matching one
            # Note: Cognito doesn't support filtering by custom attributes directly
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Filter=f'sub = "{customer_id}"',
                Limit=1
            )

            if not response.get('Users'):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )

            user = response['Users'][0]
            attributes = {attr['Name']: attr['Value'] for attr in user['Attributes']}

            return {
                "customer_id": attributes.get('sub'),
                "email": attributes.get('email'),
                "name": attributes.get('name', ''),
                "phone_number": attributes.get('phone_number'),
                "customer_folder": f"customers/{customer_id}",
                "created_date": user['UserCreateDate'].isoformat(),
                "enabled": user['Enabled'],
                "user_status": user.get('UserStatus', 'UNKNOWN')
            }

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to get customer: {str(e)}"
            )

    def update_customer(
        self,
        customer_id: str,
        name: str | None = None,
        phone_number: str | None = None,
        enabled: bool | None = None
    ) -> Dict[str, Any]:
        """
        Update customer profile.

        Args:
            customer_id: Customer's unique ID
            name: New name (optional)
            phone_number: New phone number in E.164 format (optional)
            enabled: Enable/disable account (optional)

        Returns:
            Updated customer profile

        Raises:
            HTTPException: If update fails
        """
        try:
            # Validate phone number format if provided
            if phone_number is not None:
                phone_number = phone_number.strip()
                if phone_number and not phone_number.startswith('+'):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Phone number must be in E.164 format (e.g., +1234567890)"
                    )
                if phone_number and (not phone_number[1:].isdigit() or len(phone_number) < 8 or len(phone_number) > 16):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid phone number format. Must be E.164 format with country code (e.g., +1234567890)"
                    )

            # First, get the customer to find their username (email)
            customer = self.get_customer(customer_id)
            username = customer['email']

            # Update attributes
            user_attributes = []
            if name is not None:
                user_attributes.append({"Name": "name", "Value": name})
            if phone_number is not None:
                user_attributes.append({"Name": "phone_number", "Value": phone_number})
                user_attributes.append({"Name": "phone_number_verified", "Value": "true"})

            if user_attributes:
                self.client.admin_update_user_attributes(
                    UserPoolId=self.user_pool_id,
                    Username=username,
                    UserAttributes=user_attributes
                )

            # Enable/disable user
            if enabled is not None:
                if enabled:
                    self.client.admin_enable_user(
                        UserPoolId=self.user_pool_id,
                        Username=username
                    )
                else:
                    self.client.admin_disable_user(
                        UserPoolId=self.user_pool_id,
                        Username=username
                    )

            # Return updated customer profile
            return self.get_customer(customer_id)

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update customer: {str(e)}"
            )

    def resend_customer_welcome(
        self,
        customer_id: str
    ) -> Dict[str, Any]:
        """
        Reset customer password and resend welcome email.

        Useful when:
        - Customer didn't receive the original email
        - Temporary password expired (7 days)
        - Customer lost their password

        Cannot be used if customer has already set their own password.

        Args:
            customer_id: Customer's unique ID

        Returns:
            Dictionary with customer details and new temporary password

        Raises:
            HTTPException: If reset fails or user already changed password
        """
        try:
            # Get the customer to find their email
            customer = self.get_customer(customer_id)
            username = customer['email']

            # Check user status to see if they've already changed their password
            user_response = self.client.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )

            # Check UserStatus - if CONFIRMED, they've already set their own password
            user_status = user_response.get('UserStatus')
            if user_status == 'CONFIRMED':
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot resend welcome email. Customer has already set their own password. Use the forgot password flow instead."
                )

            # Only allow resend for users who haven't completed initial setup
            # Valid statuses: FORCE_CHANGE_PASSWORD, RESET_REQUIRED
            if user_status not in ['FORCE_CHANGE_PASSWORD', 'RESET_REQUIRED']:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot resend welcome email. User status is {user_status}. This feature is only for users who haven't completed initial login."
                )

            # Generate a new temporary password
            new_temporary_password = self._generate_temporary_password()

            # Set the new temporary password
            # This will force password change on next login
            self.client.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=username,
                Password=new_temporary_password,
                Permanent=False  # User must change on first login
            )

            # Send welcome email via SES with new password
            email_service.send_welcome_email(
                recipient_email=username,
                recipient_name=customer['name'],
                temporary_password=new_temporary_password
            )

            return {
                "customer_id": customer_id,
                "email": username,
                "name": customer['name'],
                "temporary_password": new_temporary_password,
                "message": "Welcome email resent with new temporary password"
            }

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error'].get('Message', str(e))

            if error_code == 'UserNotFoundException':
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to resend welcome email: {error_message}"
                )


# Global auth instance
cognito_auth = CognitoAuth()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User claims from verified token

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    claims = cognito_auth.verify_token(token)
    return claims


async def require_admin(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency to require admin role.

    Args:
        current_user: Current authenticated user

    Returns:
        User claims if user is admin

    Raises:
        HTTPException: If user is not an admin
    """
    groups = current_user.get("cognito:groups", [])

    if "Admins" not in groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


async def require_customer(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Dependency to require customer role.

    Args:
        current_user: Current authenticated user

    Returns:
        User claims if user is customer

    Raises:
        HTTPException: If user is not a customer
    """
    groups = current_user.get("cognito:groups", [])

    if "Customers" not in groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required"
        )

    return current_user


def get_user_role(user: Dict[str, Any]) -> str:
    """
    Get user's role from their groups.

    Args:
        user: User claims from token

    Returns:
        Role name ('admin' or 'customer')
    """
    groups = user.get("cognito:groups", [])

    if "Admins" in groups:
        return "admin"
    elif "Customers" in groups:
        return "customer"
    else:
        return "unknown"


def get_customer_id(user: Dict[str, Any]) -> str | None:
    """
    Get customer_id from user claims.

    Args:
        user: User claims from token

    Returns:
        Customer ID or None
    """
    # Try custom attribute first, then fall back to sub
    customer_id = user.get("custom:customer_id") or user.get("sub")
    return customer_id



