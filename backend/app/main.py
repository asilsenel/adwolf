"""
Ad Platform MVP - FastAPI Application

Main entry point for the FastAPI backend.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.api.v1 import router as v1_router
from app.models.common import ErrorResponse, ErrorDetail, HealthResponse


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Debug mode: {settings.debug}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description="""
    Dijital pazarlama platformlarını (Google Ads, Meta Ads) birleştiren 
    ve AI-powered insights üreten SaaS uygulaması.
    
    ## Özellikler
    
    * **OAuth Bağlantı** - Google Ads ve Meta Ads hesaplarını güvenli şekilde bağla
    * **Metrik Senkronizasyonu** - Günlük performans verilerini otomatik çek
    * **Unified Dashboard** - Tüm platformları tek ekranda gör
    * **AI Insights** - GPT-4 ile otomatik analiz ve öneriler
    * **Günlük Özet** - Email/WhatsApp ile daily digest al
    
    ## Authentication
    
    1. POST `/api/v1/auth/login` ile email/password gönderin
    2. Dönen `access_token`'ı kopyalayın
    3. Sağ üstteki "Authorize" butonuna tıklayın
    4. Token'ı `Bearer <token>` formatında girin
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# Custom OpenAPI schema with security
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "POST /api/v1/auth/login ile aldığınız access_token'ı girin",
        }
    }
    
    # Apply security globally (optional - endpoints can override)
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# CORS Middleware - Convert AnyHttpUrl to strings and strip trailing slashes
cors_origins = [str(origin).rstrip("/") for origin in settings.backend_cors_origins]
# Add localhost variants for development
if settings.debug:
    cors_origins.extend([
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ])
    # Remove duplicates
    cors_origins = list(set(cors_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="Bir hata oluştu. Lütfen daha sonra tekrar deneyin.",
                details={"error": str(exc)} if settings.debug else None,
            )
        ).model_dump(),
    )


# Include API routers
app.include_router(v1_router, prefix="/api")


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the application status and version.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint with API info."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs" if settings.debug else "Disabled in production",
        "health": "/health",
    }


# Ready endpoint (for Kubernetes/Railway probes)
@app.get("/ready", tags=["System"])
async def ready():
    """Readiness probe endpoint."""
    # TODO: Check database connection, Redis, etc.
    return {"ready": True}
