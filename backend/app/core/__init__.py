"""
Ad Platform MVP - Core Module

Core utilities and configuration.
"""

from app.core.config import settings, get_settings
from app.core.supabase import get_supabase_client, get_supabase_service, SupabaseService
from app.core.security import (
    encrypt_token,
    decrypt_token,
    create_access_token,
    decode_access_token,
    verify_token,
    generate_oauth_state,
    create_oauth_state_token,
    decode_oauth_state_token,
)

__all__ = [
    # Config
    "settings",
    "get_settings",
    # Supabase
    "get_supabase_client",
    "get_supabase_service",
    "SupabaseService",
    # Security
    "encrypt_token",
    "decrypt_token",
    "create_access_token",
    "decode_access_token",
    "verify_token",
    "generate_oauth_state",
    "create_oauth_state_token",
    "decode_oauth_state_token",
]
