"""
Hovver Admin Dashboard Backend API
FastAPI application for managing commercial photography with AWS Cognito auth and S3 storage.
"""
from typing import Dict, Any, List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from config import settings
from auth import cognito_auth, get_current_user
from s3_service import s3_service


# Security scheme
security = HTTPBearer()


# Pydantic models for request/response
class LoginRequest(BaseModel):
    """Login request model."""
    username: str = Field(..., description="User's username")
    password: str = Field(..., description="User's password")


class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    id_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class ChangePasswordRequest(BaseModel):
    """Change password request model."""
    old_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class ForgotPasswordRequest(BaseModel):
    """Forgot password request model."""
    username: str = Field(..., description="User's email address")


class ResetPasswordRequest(BaseModel):
    """Reset password request model."""
    username: str = Field(..., description="User's email address")
    confirmation_code: str = Field(..., description="Confirmation code from email")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")


class CompleteNewPasswordRequest(BaseModel):
    """Complete new password challenge request model."""
    username: str = Field(..., description="User's email address")
    temporary_password: str = Field(..., description="Temporary password from admin")
    new_password: str = Field(..., min_length=8, description="New permanent password (min 8 characters)")


class UpdateUserAttributesRequest(BaseModel):
    """Update user attributes request model."""
    email: str | None = Field(None, description="New email address")
    name: str | None = Field(None, description="User's full name")
    phone_number: str | None = Field(None, description="Phone number in E.164 format")


class UpdateProfileRequest(BaseModel):
    """Update user profile request model."""
    full_name: str | None = Field(None, description="User's full name")
    phone_number: str | None = Field(None, description="Phone number in E.164 format (+1234567890)")


class RefreshTokenRequest(BaseModel):
    """Refresh token request model."""
    refresh_token: str = Field(..., description="Refresh token from login")


class MessageResponse(BaseModel):
    """Generic message response model."""
    message: str
    success: bool = True


class UploadResponse(BaseModel):
    """Image upload response model."""
    success: bool
    key: str
    filename: str
    size: int
    content_type: str
    upload_date: str
    message: str = "Image uploaded successfully"


class ImageInfo(BaseModel):
    """Image information model."""
    key: str
    size: int
    last_modified: str
    presigned_url: str
    content_type: str
    metadata: Dict[str, Any]


class ImagesListResponse(BaseModel):
    """Images list response model."""
    count: int
    images: List[ImageInfo]


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    app_name: str
    version: str
    environment: str


# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Admin Dashboard Backend for Commercial Photography Website with AWS Cognito authentication and S3 image management",
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get(
    "/",
    response_model=HealthResponse,
    tags=["Health"]
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }


# Authentication endpoints
@app.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    tags=["Authentication"],
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


@app.get(
    "/auth/me",
    response_model=Dict[str, Any],
    tags=["Authentication"],
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


@app.post(
    "/auth/change-password",
    response_model=MessageResponse,
    tags=["User Management"],
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


@app.post(
    "/auth/forgot-password",
    response_model=MessageResponse,
    tags=["User Management"],
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


@app.post(
    "/auth/reset-password",
    response_model=MessageResponse,
    tags=["User Management"],
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


@app.post(
    "/auth/complete-new-password",
    response_model=LoginResponse,
    tags=["User Management"],
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


@app.put(
    "/auth/profile",
    response_model=MessageResponse,
    tags=["User Management"],
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
        import logging
        logging.error(f"Profile update error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile: {str(e)}"
        )


@app.post(
    "/auth/refresh",
    response_model=Dict[str, Any],
    tags=["Authentication"],
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


@app.get(
    "/auth/user-info",
    response_model=Dict[str, Any],
    tags=["User Management"],
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


# Image management endpoints
@app.post(
    "/images/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Images"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Upload failed"}
    }
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Upload an image to S3 bucket.

    Requires authentication. Images are organized by upload date.
    Supported formats: JPEG, PNG, WebP, GIF
    Maximum file size: 10MB
    """
    username = current_user.get("username") or current_user.get("cognito:username")
    result = await s3_service.upload_image(file, username=username)
    return result


@app.get(
    "/images/list",
    response_model=ImagesListResponse,
    tags=["Images"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Failed to retrieve images"}
    }
)
async def list_images(
    prefix: str = "",
    max_keys: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all images in S3 bucket with presigned URLs.

    Requires authentication. Returns presigned URLs valid for 1 hour.

    - **prefix**: Optional path prefix to filter results
    - **max_keys**: Maximum number of images to return (default: 100)
    """
    images = s3_service.list_images(prefix=prefix, max_keys=max_keys)
    return {
        "count": len(images),
        "images": images
    }


@app.delete(
    "/images/{key:path}",
    response_model=Dict[str, Any],
    tags=["Images"],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        500: {"model": ErrorResponse, "description": "Failed to delete image"}
    }
)
async def delete_image(
    key: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete an image from S3 bucket.

    Requires authentication.

    - **key**: S3 object key (path) of the image to delete
    """
    success = s3_service.delete_image(key)
    return {
        "success": success,
        "message": f"Image {key} deleted successfully"
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error": str(exc)
        }
    )
