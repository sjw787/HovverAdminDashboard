"""
Services for authentication, storage, and email.
"""
from api.services.auth import (
    cognito_auth,
    get_current_user,
    require_admin,
    require_customer,
    get_user_role,
    get_customer_id,
    security
)
from api.services.s3 import s3_service
from api.services.email import email_service

__all__ = [
    'cognito_auth',
    'get_current_user',
    'require_admin',
    'require_customer',
    'get_user_role',
    'get_customer_id',
    'security',
    's3_service',
    'email_service'
]
