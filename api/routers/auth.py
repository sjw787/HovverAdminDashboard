"""
Authentication and user management routes.
"""
from typing import Dict, Any
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from api.models import (
    LoginRequest, LoginResponse, ChangePasswordRequest, ForgotPasswordRequest,
    ResetPasswordRequest, CompleteNewPasswordRequest, UpdateProfileRequest,
    RefreshTokenRequest, MessageResponse, ErrorResponse
)
from api.services import cognito_auth, get_current_user, security

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": ErrorResponse, "description": "Authentication failed"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def login(login_data: LoginRequest):
    """
    Authenticate user with AWS Cognito.

    Returns JWT tokens for authenticated session.
    """
    return cognito_auth.authenticate_user(
        username=login_data.username,
        password=login_data.password
    )


@router.get(
    "/me",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_current_user_info(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    return {
        "username": current_user.get("username") or current_user.get("cognito:username"),
        "email": current_user.get("email"),
        "sub": current_user.get("sub"),
        "token_use": current_user.get("token_use")
    }


@router.post(
    "/change-password",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized or incorrect password"},
        400: {"model": ErrorResponse, "description": "Invalid password format"},
        429: {"model": ErrorResponse, "description": "Too many attempts"}
    }
)
async def change_password(
    request: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Change user's password.

    Requires authentication. User must provide current password.
    """
    result = cognito_auth.change_password(
        access_token=credentials.credentials,
        old_password=request.old_password,
        new_password=request.new_password
    )
    return MessageResponse(**result)


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid email"},
        429: {"model": ErrorResponse, "description": "Too many attempts"}
    }
)
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiate forgot password flow.

    Sends a confirmation code to the user's email address.
    No authentication required.
    """
    result = cognito_auth.forgot_password(username=request.username)
    return MessageResponse(**result)


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid code or password"},
        429: {"model": ErrorResponse, "description": "Too many attempts"}
    }
)
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with confirmation code.

    Complete the forgot password flow by providing the code from email.
    No authentication required.
    """
    result = cognito_auth.confirm_forgot_password(
        username=request.username,
        confirmation_code=request.confirmation_code,
        new_password=request.new_password
    )
    return MessageResponse(**result)


@router.post(
    "/complete-new-password",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        400: {"model": ErrorResponse, "description": "Invalid password format"},
        429: {"model": ErrorResponse, "description": "Too many attempts"}
    }
)
async def complete_new_password(request: CompleteNewPasswordRequest):
    """
    Complete new password challenge for users with temporary passwords.

    When an admin creates a user or resets a password, the user receives a temporary
    password. On first login, they must set a new permanent password.

    This endpoint handles the NEW_PASSWORD_REQUIRED challenge from Cognito.
    Returns authentication tokens upon successful password change.

    No authentication required - uses temporary password for verification.
    """
    result = cognito_auth.complete_new_password_challenge(
        username=request.username,
        temporary_password=request.temporary_password,
        new_password=request.new_password
    )
    return LoginResponse(**result)


@router.put(
    "/profile",
    response_model=MessageResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        400: {"model": ErrorResponse, "description": "Invalid attribute value"}
    }
)
async def update_profile(
    request: UpdateProfileRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Update user profile attributes.

    Requires authentication. Can update full name and phone number.
    Both fields are optional - only include fields you want to update.
    """
    try:
        # Build attributes dict with only non-None and non-empty values
        attributes = {}
        if request.full_name and request.full_name.strip():
            attributes["name"] = request.full_name.strip()
        if request.phone_number and request.phone_number.strip():
            attributes["phone_number"] = request.phone_number.strip()

        # Check if at least one attribute was provided
        if not attributes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide at least one field to update (full_name or phone_number)"
            )

        result = cognito_auth.update_user_attributes(
            access_token=credentials.credentials,
            attributes=attributes
        )
        return MessageResponse(**result)
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log unexpected errors
        logging.error(f"Profile update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@router.post(
    "/refresh",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"}
    }
)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token.

    Use the refresh token from login to get new access and ID tokens.
    No authentication required - just provide refresh token.
    """
    return cognito_auth.refresh_access_token(refresh_token=request.refresh_token)


@router.get(
    "/user-info",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"}
    }
)
async def get_detailed_user_info(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Get detailed user information including all Cognito attributes.

    Requires authentication. Returns full user profile with all attributes.
    """
    return cognito_auth.get_user_info(access_token=credentials.credentials)

