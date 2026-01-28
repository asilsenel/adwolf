"""
Ad Platform MVP - Common Response Models

Common response wrappers and error models.
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response wrapper."""
    success: bool = True
    data: T
    meta: Optional[dict] = None


class ErrorDetail(BaseModel):
    """Error detail model."""
    code: str
    message: str
    details: Optional[dict] = None
    field: Optional[str] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = False
    error: ErrorDetail


class PaginationMeta(BaseModel):
    """Pagination metadata."""
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    total: int = Field(..., ge=0)
    total_pages: int = Field(..., ge=0)

    @classmethod
    def calculate(cls, page: int, per_page: int, total: int) -> "PaginationMeta":
        """Calculate pagination metadata."""
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        return cls(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    success: bool = True
    data: list[T]
    meta: PaginationMeta


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    timestamp: str


# ===========================================
# COMMON ERROR CODES
# ===========================================

class ErrorCodes:
    """Common error codes."""
    # Authentication
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    
    # Authorization
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    
    # Validation
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_INPUT = "INVALID_INPUT"
    
    # Resources
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    CONFLICT = "CONFLICT"
    
    # OAuth
    OAUTH_ERROR = "OAUTH_ERROR"
    OAUTH_STATE_INVALID = "OAUTH_STATE_INVALID"
    OAUTH_TOKEN_ERROR = "OAUTH_TOKEN_ERROR"
    
    # External APIs
    PLATFORM_ERROR = "PLATFORM_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    API_ERROR = "API_ERROR"
    
    # General
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
