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
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
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
