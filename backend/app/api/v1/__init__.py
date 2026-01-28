"""
Ad Platform MVP - API v1 Module

API version 1 routers.
"""

from fastapi import APIRouter

from app.api.v1 import auth, accounts, metrics, insights


# Create main v1 router
router = APIRouter(prefix="/v1")

# Include all sub-routers
router.include_router(auth.router)
router.include_router(accounts.router)
router.include_router(metrics.router)
router.include_router(insights.router)
