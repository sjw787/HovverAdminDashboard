"""
Configuration module for AWS services and application settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # AWS Configuration
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None  # Optional, prefer IAM roles
    aws_secret_access_key: str | None = None  # Optional, prefer IAM roles

    # Cognito Configuration
    cognito_user_pool_id: str
    cognito_client_id: str
    cognito_region: str | None = None  # Defaults to aws_region if not set

    # S3 Configuration
    s3_bucket_name: str
    s3_region: str | None = None  # Defaults to aws_region if not set
    presigned_url_expiration: int = 3600  # 1 hour in seconds

    # Application Configuration
    app_name: str = "Hover Admin Dashboard"
    app_version: str = "0.1.0"
    environment: str = "development"

    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # File Upload Configuration
    max_file_size: int = 10 * 1024 * 1024  # 10MB in bytes
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]

    # Email Configuration (Resend)
    resend_api_key: str
    sender_email: str = "noreply@samwylock.com"
    sender_name: str = "Hover"
    frontend_url: str = "https://dev.samwylock.com"  # Frontend URL for email links

    @property
    def effective_cognito_region(self) -> str:
        """Get the effective Cognito region."""
        return self.cognito_region or self.aws_region

    @property
    def effective_s3_region(self) -> str:
        """Get the effective S3 region."""
        return self.s3_region or self.aws_region


# Global settings instance
settings = Settings()

