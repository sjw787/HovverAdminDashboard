"""
Hovver Admin Dashboard Backend API
FastAPI application for managing commercial photography with AWS Cognito auth and S3 storage.
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from api.models import HealthResponse
from api.routers import auth_router, images_router, customers_router


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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


# Include routers
app.include_router(auth_router)
app.include_router(images_router)
app.include_router(customers_router)


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


# CORS diagnostic endpoint
@app.get(
    "/cors-test",
    tags=["Health"]
)
async def cors_test(request: Request):
    """Test CORS configuration."""
    return {
        "message": "CORS is working!",
        "origin": request.headers.get("origin"),
        "allowed_origins": settings.cors_origins,
        "user_agent": request.headers.get("user-agent")
    }


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with CORS headers."""
    origin = request.headers.get("origin")

    # Prepare response
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code
        }
    )

    # Add CORS headers if origin is in allowed list
    if origin and origin in settings.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with CORS headers."""
    origin = request.headers.get("origin")

    # Prepare response
    response = JSONResponse(
        status_code=500,
        content={
            "detail": "An unexpected error occurred",
            "error": str(exc)
        }
    )

    # Add CORS headers if origin is in allowed list
    if origin and origin in settings.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"

    return response

