"""
Image management routes.
"""
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException, status

from api.models import UploadResponse, ImagesListResponse, ErrorResponse
from api.services import s3_service, get_current_user, get_user_role, get_customer_id, require_admin


router = APIRouter(prefix="/images", tags=["Images"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file"},
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Forbidden - customer_id required for customers"},
        500: {"model": ErrorResponse, "description": "Upload failed"}
    }
)
async def upload_image(
    file: UploadFile = File(..., description="Image file to upload"),
    customer_id: Optional[str] = Query(None, description="Customer ID (admin: any ID or None for general; customer: must match their ID)"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Upload an image to S3 bucket.

    Requires authentication.

    **Admin users:**
    - Can upload to any customer folder by specifying customer_id
    - Can upload to general folder by omitting customer_id (or setting to None)

    **Customer users:**
    - Can only view files, not upload (403 Forbidden)

    Supported formats: JPEG, PNG, WebP, GIF
    Maximum file size: 10MB
    """
    username = current_user.get("username") or current_user.get("cognito:username")
    user_role = get_user_role(current_user)
    user_customer_id = get_customer_id(current_user)

    # Check permissions
    if user_role == "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers cannot upload files. Contact an administrator."
        )

    # Admin can upload to any customer folder or general folder
    if user_role == "admin":
        target_customer_id = customer_id  # Can be None for general folder
    else:
        # Unknown role - deny access
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to upload files"
        )

    result = await s3_service.upload_image(
        file,
        customer_id=target_customer_id,
        username=username
    )
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
    prefix: str = Query("", description="Optional path prefix to filter results (admin only)"),
    max_keys: int = Query(100, description="Maximum number of images to return", ge=1, le=1000),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List images in S3 bucket with presigned URLs.

    Requires authentication. Returns presigned URLs valid for 1 hour.

    **Admin users:**
    - See all images across all customers and general folder
    - Can filter by prefix

    **Customer users:**
    - See only their own files and general folder files
    - prefix parameter is ignored
    """
    user_role = get_user_role(current_user)
    user_customer_id = get_customer_id(current_user)

    if user_role == "admin":
        # Admins can see everything
        images = s3_service.list_images(prefix=prefix, max_keys=max_keys)
    elif user_role == "customer":
        # Customers see only their files + general files
        images = s3_service.list_images_for_customer(
            customer_id=user_customer_id,
            max_keys=max_keys
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to list files"
        )

    return {
        "count": len(images),
        "images": images
    }


@router.delete(
    "/{key:path}",
    response_model=Dict[str, Any],
    responses={
        401: {"model": ErrorResponse, "description": "Unauthorized"},
        403: {"model": ErrorResponse, "description": "Admin access required"},
        500: {"model": ErrorResponse, "description": "Failed to delete image"}
    }
)
async def delete_image(
    key: str,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Delete an image from S3 bucket.

    Admin only. Customers cannot delete files.

    - **key**: S3 object key (path) of the image to delete
    """
    success = s3_service.delete_image(key)
    return {
        "success": success,
        "message": f"Image {key} deleted successfully"
    }

