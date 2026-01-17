"""
Customer management routes (Admin only).
"""
from typing import Dict, Any

from fastapi import APIRouter, Depends, status

from api.models import (
    CreateCustomerRequest,
    CustomerProfileResponse,
    CustomerCreatedResponse,
    ResendWelcomeResponse,
    UpdateCustomerRequest,
    CustomerListResponse,
    ErrorResponse
)
from api.services import cognito_auth, require_admin


router = APIRouter(prefix="/customers", tags=["Customer Management"])


@router.post(
    "",
    response_model=CustomerCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"model": ErrorResponse, "description": "Admin access required"},
        409: {"model": ErrorResponse, "description": "Customer already exists"},
        400: {"model": ErrorResponse, "description": "Invalid request"}
    }
)
async def create_customer(
    request: CreateCustomerRequest,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Create a new customer profile.

    Admin only. Creates a new customer user in Cognito and assigns them to the Customers group.

    A secure temporary password is automatically generated and returned in the response.
    The customer must change this password on their first login.

    **Email is required** - used as the username for login.
    """
    customer = cognito_auth.create_customer(
        email=request.email,
        name=request.name,
        phone_number=request.phone_number
    )
    return customer


@router.get(
    "",
    response_model=CustomerListResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Admin access required"}
    }
)
async def list_customers(
    limit: int = 60,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    List all customer profiles.

    Admin only. Returns a list of all customers in the Customers group.
    """
    customers = cognito_auth.list_customers(limit=limit)
    return {
        "count": len(customers),
        "customers": customers
    }


@router.get(
    "/{customer_id}",
    response_model=CustomerProfileResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Admin access required"},
        404: {"model": ErrorResponse, "description": "Customer not found"}
    }
)
async def get_customer(
    customer_id: str,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Get a specific customer profile.

    Admin only. Returns detailed information about a customer.
    """
    customer = cognito_auth.get_customer(customer_id)
    return customer


@router.patch(
    "/{customer_id}",
    response_model=CustomerProfileResponse,
    responses={
        403: {"model": ErrorResponse, "description": "Admin access required"},
        404: {"model": ErrorResponse, "description": "Customer not found"}
    }
)
async def update_customer(
    customer_id: str,
    request: UpdateCustomerRequest,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Update a customer profile.

    Admin only. Updates customer information such as name, phone number, or account status.
    """
    customer = cognito_auth.update_customer(
        customer_id=customer_id,
        name=request.name,
        phone_number=request.phone_number,
        enabled=request.enabled
    )
    return customer


@router.post(
    "/{customer_id}/resend-welcome",
    response_model=ResendWelcomeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Customer already set their own password"},
        403: {"model": ErrorResponse, "description": "Admin access required"},
        404: {"model": ErrorResponse, "description": "Customer not found"},
        500: {"model": ErrorResponse, "description": "Failed to resend email"}
    }
)
async def resend_welcome_email(
    customer_id: str,
    admin_user: Dict[str, Any] = Depends(require_admin)
):
    """
    Resend welcome email with new temporary password.

    Admin only. Generates a new temporary password and sends a welcome email via AWS SES.

    **Use cases:**
    - Customer didn't receive original email
    - Temporary password expired (after 7 days)
    - Customer lost/forgot their temporary password
    - Customer never completed initial login

    **Restrictions:**
    - Cannot be used if customer has already set their own password
    - Only works for users in FORCE_CHANGE_PASSWORD or RESET_REQUIRED status
    - For customers who already changed their password, use the forgot password flow instead

    The new temporary password must be changed on first login.
    Email is sent via AWS SES with professional HTML template.
    """
    result = cognito_auth.resend_customer_welcome(customer_id=customer_id)
    return result


