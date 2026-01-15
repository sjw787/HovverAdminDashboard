"""
Hovver Admin Dashboard Backend API
FastAPI application for managing commercial photography with AWS Cognito auth and S3 storage.
"""
from typing import Dict, Any, List

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from config import settings
from auth import cognito_auth, get_current_user
from s3_service import s3_service


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
