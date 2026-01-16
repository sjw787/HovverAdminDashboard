"""
Authentication service using AWS Cognito.
"""
import json
from typing import Dict, Any
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, jwk
from jose.utils import base64url_decode
import requests

from config import settings


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

