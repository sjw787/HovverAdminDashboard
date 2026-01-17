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


# Customer Management Models
class CreateCustomerRequest(BaseModel):
    """Create customer request model."""
    email: str = Field(..., description="Customer's email address (required)")
    name: str = Field(..., description="Customer's full name")
    phone_number: str | None = Field(None, description="Phone number in E.164 format (+1234567890)")


class CustomerProfileResponse(BaseModel):
    """Customer profile response model."""
    customer_id: str = Field(..., description="Unique customer ID (Cognito sub)")
    email: str
    name: str
    phone_number: str | None = None
    customer_folder: str = Field(..., description="S3 folder path for customer files")
    created_date: str
    enabled: bool = True
    user_status: str = Field(..., description="Cognito user status (FORCE_CHANGE_PASSWORD, CONFIRMED, etc.)")


class CustomerCreatedResponse(CustomerProfileResponse):
    """Customer created response model with temporary password."""
    temporary_password: str = Field(..., description="Auto-generated temporary password (must be changed on first login)")


class ResendWelcomeResponse(BaseModel):
    """Response for resending welcome email."""
    customer_id: str = Field(..., description="Customer ID")
    email: str = Field(..., description="Customer email")
    name: str = Field(..., description="Customer name")
    temporary_password: str = Field(..., description="New temporary password")
    message: str = Field(..., description="Success message")


class UpdateCustomerRequest(BaseModel):
    """Update customer request model."""
    name: str | None = Field(None, description="Customer's full name")
    phone_number: str | None = Field(None, description="Phone number in E.164 format")
    enabled: bool | None = Field(None, description="Enable or disable customer account")


class CustomerListResponse(BaseModel):
    """Customer list response model."""
    count: int
    customers: List[CustomerProfileResponse]


# Image Models
class UploadResponse(BaseModel):
    """Image upload response model."""
    success: bool
    key: str
    filename: str
    size: int
    content_type: str
    upload_date: str
    customer_id: str | None = None
    folder: str
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

