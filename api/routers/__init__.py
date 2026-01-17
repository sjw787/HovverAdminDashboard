"""
API routers.
"""
from api.routers.auth import router as auth_router
from api.routers.images import router as images_router
from api.routers.customers import router as customers_router

__all__ = ['auth_router', 'images_router', 'customers_router']
