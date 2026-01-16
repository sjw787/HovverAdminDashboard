"""
Pydantic models for request/response validation.
"""
from typing import Dict, Any, List
from pydantic import BaseModel, Field


# Authentication Models
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


# Image Models
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


# Common Models
class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    app_name: str
    version: str
    environment: str

