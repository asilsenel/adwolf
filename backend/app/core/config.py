"""
Ad Platform MVP - Application Settings

Centralized configuration using Pydantic Settings.
All environment variables are loaded and validated here.
"""

from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===========================================
    # APPLICATION
    # ===========================================
    app_name: str = "Ad Platform MVP"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: str = "INFO"
    default_timezone: str = "Europe/Istanbul"

    # ===========================================
    # SUPABASE
    # ===========================================
    supabase_url: str
    supabase_service_role_key: str

    # ===========================================
    # GOOGLE ADS
    # ===========================================
    google_ads_client_id: str
    google_ads_client_secret: str
    google_ads_developer_token: str
    google_ads_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # ===========================================
    # META ADS
    # ===========================================
    meta_app_id: str
    meta_app_secret: str
    meta_redirect_uri: str = "http://localhost:8000/api/v1/auth/meta/callback"

    # ===========================================
    # OPENAI
    # ===========================================
    openai_api_key: str
    openai_model: str = "gpt-4o"

    # ===========================================
    # REDIS
    # ===========================================
    redis_url: str = "redis://redis:6379/0"

    # ===========================================
    # SECURITY
    # ===========================================
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    encryption_key: str  # 64 hex characters for AES-256

    # ===========================================
    # CORS
    # ===========================================
    frontend_url: str = "http://localhost:3000"

    # ===========================================
    # RATE LIMITING
    # ===========================================
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        """Validate that encryption key is proper length for AES-256."""
        if len(v) != 64:
            raise ValueError(
                "ENCRYPTION_KEY must be 64 hex characters (32 bytes for AES-256)"
            )
        try:
            bytes.fromhex(v)
        except ValueError:
            raise ValueError("ENCRYPTION_KEY must be valid hexadecimal")
        return v

    @property
    def encryption_key_bytes(self) -> bytes:
        """Get encryption key as bytes."""
        return bytes.fromhex(self.encryption_key)

    @property
    def cors_origins(self) -> list[str]:
        """Get list of allowed CORS origins."""
        origins = [self.frontend_url]
        if self.debug:
            origins.extend([
                "http://localhost:3000",
                "http://localhost:3001",
                "http://127.0.0.1:3000",
            ])
        return origins


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Uses lru_cache for performance - settings are loaded once and reused.
    """
    return Settings()


# Convenience export
settings = get_settings()
