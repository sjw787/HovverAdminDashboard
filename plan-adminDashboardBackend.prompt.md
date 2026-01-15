# Plan: Build Admin Dashboard Backend with AWS Cognito Auth and S3 Image Management

This plan outlines building a FastAPI backend service for a commercial photography admin dashboard. The system will implement AWS Cognito authentication (username/password), S3-based image upload functionality, and an endpoint to list/preview images from the bucket. The architecture will use boto3 for AWS integration and JWT tokens for session management.

## Steps

1. Add required dependencies to [pyproject.toml](C:\Users\Sam\PycharmProjects\HovverAdminDashboard\pyproject.toml): `boto3`, `python-jose[cryptography]`, `python-multipart`, `pydantic-settings`

2. Create configuration module (`config.py`) to manage AWS credentials, Cognito pool IDs, S3 bucket name, and region settings using environment variables

3. Implement authentication service (`auth.py`) with Cognito user pool integration: login endpoint, token validation middleware, and JWT verification functions

4. Build S3 service module (`s3_service.py`) with functions for uploading images (with content-type validation), generating presigned URLs, and listing bucket objects with metadata

5. Create API endpoints in [main.py](C:\Users\Sam\PycharmProjects\HovverAdminDashboard\main.py): `/auth/login` (POST), `/images/upload` (POST, protected), `/images/list` (GET, protected) with appropriate request/response models

6. Add CORS middleware configuration and proper error handling with structured exception responses for AWS service failures 

7. This project should be deployed via terraform scripts for all AWS resources (Cognito User Pool, S3 Bucket) and the FastAPI application itself on ECS Fargate with an API Gateway proxy.

8. Images should be organized by date uplaoded in the S3 bucket.

9. AWS Iam roles should be used for authentication instead of access keys. 

10. An administrative user should be created in the Cognito User Pool for accessing the dashboard.

11. The list endpoint should return presigned URLs for image previews.

