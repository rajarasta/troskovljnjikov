"""API Key Authentication for BOQ Matcher API.

This module provides basic API key authentication that can be added to secure endpoints.
Currently, it supports:
- Optional API key validation (controlled via environment variable)
- Per-endpoint authentication

Usage:
    @router.post("/protected-endpoint")
    async def protected(authenticated: bool = Depends(require_api_key)):
        # Only called if API key is valid or auth is disabled
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Header, status
from typing import Optional

from app.config import settings


# In-memory API key store (in production, use a database)
# Map of API key -> metadata (e.g., name, rate limit)
VALID_API_KEYS = {
    # Keys can be generated and stored here or in a database
    # Format: "api_key_string": {"name": "client_name", "created": "date"}
}


def _get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> Optional[str]:
    """Extract API key from request headers."""
    return x_api_key


async def require_api_key(
    api_key: Optional[str] = Depends(_get_api_key_from_header),
) -> bool:
    """
    Dependency that validates API key if AUTH_ENABLED is True.

    If AUTH_ENABLED is False (default for development), this always returns True.
    If AUTH_ENABLED is True, a valid X-API-Key header is required.

    Returns:
        True if authentication passed or is disabled

    Raises:
        HTTPException 401: If authentication is enabled but API key is missing or invalid
    """
    # If auth is disabled, allow all requests (default for development)
    if not settings.AUTH_ENABLED:
        return True

    # Auth is enabled, validate the API key
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Include 'X-API-Key' header.",
            headers={"WWW-Authenticate": "ApiKeyAuth"},
        )

    if api_key not in VALID_API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKeyAuth"},
        )

    return True


def add_api_key(key: str, name: str) -> None:
    """
    Add an API key to the valid keys store.

    In production, this should be replaced with database operations
    and proper key generation (e.g., using secrets module).

    Args:
        key: The API key string
        name: Human-readable name for this key (e.g., client name)
    """
    VALID_API_KEYS[key] = {"name": name}


def remove_api_key(key: str) -> bool:
    """Remove an API key from valid keys. Returns True if key was removed."""
    if key in VALID_API_KEYS:
        del VALID_API_KEYS[key]
        return True
    return False


def get_api_keys_info() -> dict[str, dict]:
    """Get information about all valid API keys (without revealing the keys themselves)."""
    return {k: v for k, v in VALID_API_KEYS.items()}
