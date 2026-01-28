"""
Ad Platform MVP - Security Utilities

Token encryption/decryption and JWT handling.
Uses AES-256-GCM for encrypting OAuth tokens at rest.
"""

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings


# Password hashing context (if needed for API keys, etc.)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ===========================================
# AES-256-GCM TOKEN ENCRYPTION
# ===========================================

class TokenEncryption:
    """
    AES-256-GCM encryption for OAuth tokens.
    
    Tokens are encrypted before storing in database and
    decrypted when needed for API calls.
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with encryption key.
        
        Args:
            key: 32-byte encryption key. Uses settings if not provided.
        """
        self._key = key or settings.encryption_key_bytes
        self._aesgcm = AESGCM(self._key)

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a string using AES-256-GCM.
        
        Args:
            plaintext: The string to encrypt (e.g., OAuth token)
            
        Returns:
            Base64-encoded encrypted string with nonce prepended
        """
        # Generate random 12-byte nonce
        nonce = os.urandom(12)
        
        # Encrypt
        ciphertext = self._aesgcm.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            None  # No additional authenticated data
        )
        
        # Combine nonce + ciphertext and base64 encode
        encrypted = base64.b64encode(nonce + ciphertext).decode("utf-8")
        return encrypted

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an AES-256-GCM encrypted string.
        
        Args:
            encrypted: Base64-encoded encrypted string with nonce
            
        Returns:
            Decrypted plaintext string
            
        Raises:
            ValueError: If decryption fails (tampering or wrong key)
        """
        try:
            # Decode from base64
            data = base64.b64decode(encrypted.encode("utf-8"))
            
            # Extract nonce (first 12 bytes) and ciphertext
            nonce = data[:12]
            ciphertext = data[12:]
            
            # Decrypt
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
            
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")


# Singleton instance
_token_encryption = TokenEncryption()


def encrypt_token(token: str) -> str:
    """Encrypt an OAuth token for storage."""
    return _token_encryption.encrypt(token)


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an OAuth token from storage."""
    return _token_encryption.decrypt(encrypted_token)


# ===========================================
# JWT TOKEN HANDLING
# ===========================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time delta
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_expire_minutes
        )
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded payload dict or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> Optional[str]:
    """
    Verify token and extract user ID.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID if valid, None otherwise
    """
    payload = decode_access_token(token)
    if payload is None:
        return None
    
    user_id: str = payload.get("sub")
    if user_id is None:
        return None
    
    return user_id


# ===========================================
# OAUTH STATE TOKEN
# ===========================================

def generate_oauth_state() -> str:
    """
    Generate a secure random state token for OAuth flows.
    
    Returns:
        URL-safe random string (32 characters)
    """
    return secrets.token_urlsafe(24)


def create_oauth_state_token(
    user_id: str,
    platform: str,
    redirect_uri: Optional[str] = None
) -> str:
    """
    Create a JWT token for OAuth state parameter.
    
    This token encodes the user context and is verified
    when the OAuth callback is received.
    
    Args:
        user_id: The user initiating OAuth
        platform: Target platform (google_ads, meta_ads)
        redirect_uri: Where to redirect after success
        
    Returns:
        JWT token to use as OAuth state parameter
    """
    data = {
        "sub": user_id,
        "platform": platform,
        "redirect_uri": redirect_uri,
        "nonce": secrets.token_hex(8),
    }
    
    # Short expiration for OAuth state (10 minutes)
    return create_access_token(data, expires_delta=timedelta(minutes=10))


def decode_oauth_state_token(state: str) -> Optional[dict[str, Any]]:
    """
    Decode OAuth state token.
    
    Args:
        state: OAuth state parameter (JWT token)
        
    Returns:
        Decoded state data or None if invalid
    """
    return decode_access_token(state)


# ===========================================
# PASSWORD UTILITIES (for API keys, etc.)
# ===========================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.
    
    Returns:
        Tuple of (api_key, hashed_api_key)
        - api_key: Display to user once
        - hashed_api_key: Store in database
    """
    api_key = secrets.token_urlsafe(32)
    hashed = hash_password(api_key)
    return api_key, hashed
