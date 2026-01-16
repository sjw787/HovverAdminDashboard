"""
Image management routes.
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, UploadFile, File, status

from api.models import UploadResponse, ImagesListResponse, ErrorResponse
from api.services import s3_service, get_current_user


router = APIRouter(prefix="/images", tags=["Images"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
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


@router.get(
    "/list",
    response_model=ImagesListResponse,
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


@router.delete(
    "/{key:path}",
    response_model=Dict[str, Any],
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

