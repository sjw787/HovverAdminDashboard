"""
S3 service for image upload and management.
"""
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile, status

from config import settings


class S3Service:
    """AWS S3 service for image management."""

    def __init__(self):
        self.bucket_name = settings.s3_bucket_name
        self.region = settings.effective_s3_region
        self.presigned_url_expiration = settings.presigned_url_expiration

        # Initialize S3 client with signature version 4 for HTTPS URLs
        # Only use explicit credentials if both are provided and non-empty
        # if settings.aws_access_key_id and settings.aws_secret_access_key:
        #     self.client = boto3.client(
        #         's3',
        #         region_name=self.region,
        #         aws_access_key_id=settings.aws_access_key_id,
        #         aws_secret_access_key=settings.aws_secret_access_key,
        #         config=boto3.session.Config(signature_version='s3v4')
        #     )
        # else:
        #     # Use IAM role credentials (for ECS tasks) or default credential chain
        from botocore.config import Config
        self.client = boto3.client(
            's3',
            region_name=self.region,
            config=Config(signature_version='s3v4')
        )

    def _generate_s3_key(self, filename: str, customer_id: str | None = None) -> str:
        """
        Generate S3 key with customer-based or general organization.

        Args:
            filename: Original filename
            customer_id: Customer ID for customer-specific files, None for general files

        Returns:
            S3 key path with customer or general prefix
        """
        now = datetime.utcnow()
        date_prefix = now.strftime("%Y/%m/%d")
        timestamp = now.strftime("%Y%m%d_%H%M%S")

        # Sanitize filename
        safe_filename = Path(filename).name
        name_parts = safe_filename.rsplit('.', 1)

        if len(name_parts) == 2:
            name, ext = name_parts
            # Add timestamp to avoid collisions
            new_filename = f"{name}_{timestamp}.{ext}"
        else:
            new_filename = f"{safe_filename}_{timestamp}"

        # Organize by customer or general folder
        if customer_id:
            return f"customers/{customer_id}/{date_prefix}/{new_filename}"
        else:
            return f"general/{date_prefix}/{new_filename}"

    def _validate_image(self, file: UploadFile) -> None:
        """
        Validate uploaded image file.

        Args:
            file: Uploaded file

        Raises:
            HTTPException: If validation fails
        """
        # Check content type
        if file.content_type not in settings.allowed_image_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed types: {', '.join(settings.allowed_image_types)}"
            )

        # Check file size (if we can determine it)
        if hasattr(file, 'size') and file.size and file.size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {max_size_mb}MB"
            )

    async def upload_image(
        self,
        file: UploadFile,
        customer_id: str | None = None,
        username: str | None = None
    ) -> Dict[str, Any]:
        """
        Upload image to S3.

        Args:
            file: Uploaded image file
            customer_id: Customer ID for customer-specific files, None for general files
            username: Optional username for metadata

        Returns:
            Dictionary with upload details

        Raises:
            HTTPException: If upload fails
        """
        # Validate the image
        self._validate_image(file)

        # Generate S3 key with customer organization
        s3_key = self._generate_s3_key(file.filename, customer_id=customer_id)

        try:
            # Read file content
            content = await file.read()

            # Prepare metadata
            metadata = {
                'original_filename': file.filename,
                'upload_date': datetime.utcnow().isoformat(),
            }

            if username:
                metadata['uploaded_by'] = username

            if customer_id:
                metadata['customer_id'] = customer_id
            else:
                metadata['folder'] = 'general'

            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type,
                Metadata=metadata
            )

            return {
                "success": True,
                "key": s3_key,
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type,
                "upload_date": metadata['upload_date'],
                "customer_id": customer_id,
                "folder": f"customers/{customer_id}" if customer_id else "general"
            }

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to upload image: {str(e)}"
            )
        finally:
            # Reset file pointer
            await file.seek(0)

    def generate_presigned_url(self, s3_key: str, expiration: int | None = None) -> str:
        """
        Generate presigned URL for S3 object.

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds

        Returns:
            Presigned URL string
        """
        if expiration is None:
            expiration = self.presigned_url_expiration

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            return url

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate presigned URL: {str(e)}"
            )

    def list_images(
        self,
        prefix: str = "",
        max_keys: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List images in S3 bucket.

        Args:
            prefix: Optional prefix to filter results
            max_keys: Maximum number of keys to return

        Returns:
            List of image dictionaries with metadata and presigned URLs
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )

            if 'Contents' not in response:
                return []

            images = []
            for obj in response['Contents']:
                # Get object metadata
                try:
                    metadata_response = self.client.head_object(
                        Bucket=self.bucket_name,
                        Key=obj['Key']
                    )

                    # Generate presigned URL
                    presigned_url = self.generate_presigned_url(obj['Key'])

                    image_info = {
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "presigned_url": presigned_url,
                        "content_type": metadata_response.get('ContentType', 'unknown'),
                        "metadata": metadata_response.get('Metadata', {})
                    }

                    images.append(image_info)

                except ClientError:
                    # Skip objects we can't access
                    continue

            return images

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list images: {str(e)}"
            )

    def list_images_for_customer(
        self,
        customer_id: str,
        max_keys: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List images accessible to a specific customer (their files + general files).

        Args:
            customer_id: Customer ID
            max_keys: Maximum number of keys to return per prefix

        Returns:
            List of image dictionaries with metadata and presigned URLs
        """
        images = []

        # Get customer-specific images
        customer_prefix = f"customers/{customer_id}/"
        customer_images = self.list_images(prefix=customer_prefix, max_keys=max_keys)
        images.extend(customer_images)

        # Get general images
        general_images = self.list_images(prefix="general/", max_keys=max_keys)
        images.extend(general_images)

        # Sort by last modified date (newest first)
        images.sort(key=lambda x: x['last_modified'], reverse=True)

        return images

    def delete_image(self, s3_key: str) -> bool:
        """
        Delete image from S3.

        Args:
            s3_key: S3 object key to delete

        Returns:
            True if successful

        Raises:
            HTTPException: If deletion fails
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True

        except ClientError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete image: {str(e)}"
            )


# Global S3 service instance
s3_service = S3Service()

