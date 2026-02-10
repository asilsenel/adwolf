"""
Ad Platform MVP - Application Settings
Centralized configuration using Pydantic Settings.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import AnyHttpUrl, field_validator
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
    
    # API Prefix
    api_v1_str: str = "/api/v1"

    # ===========================================
    # SUPABASE
    # ===========================================
    supabase_url: str
    supabase_service_role_key: str

    # ===========================================
    # SECURITY
    # ===========================================
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 8  # 8 gün
    encryption_key: str  # 64 hex characters

    # ===========================================
    # GOOGLE ADS (Opsiyonel - Çökmemesi için)
    # ===========================================
    google_ads_client_id: Optional[str] = None
    google_ads_client_secret: Optional[str] = None
    google_ads_developer_token: Optional[str] = None
    google_ads_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # ===========================================
    # META ADS (Opsiyonel)
    # ===========================================
    meta_app_id: Optional[str] = None
    meta_app_secret: Optional[str] = None
    meta_redirect_uri: str = "http://localhost:8000/api/v1/auth/meta/callback"

    # ===========================================
    # OPENAI
    # ===========================================
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

    # ===========================================
    # REDIS
    # ===========================================
    redis_url: str = "redis://redis:6379/0"
    
    # ===========================================
    # CORS
    # ===========================================
    backend_cors_origins: List[AnyHttpUrl] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # --- VALIDATORS ---

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if len(v) != 64:
            raise ValueError("ENCRYPTION_KEY must be 64 hex characters")
        return v

    @property
    def encryption_key_bytes(self) -> bytes:
        return bytes.fromhex(self.encryption_key)

    @property
    def cors_origins(self) -> list[str]:
        """Return CORS origins as list of strings for FastAPI middleware."""
        return [str(origin) for origin in self.backend_cors_origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()