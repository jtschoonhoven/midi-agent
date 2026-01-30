"""Authentication middleware for API key validation."""

import hashlib
import hmac
import logging
import os
from collections.abc import Awaitable, Callable
from uuid import UUID

import anthropic
from fastapi import HTTPException, Request, Response

from api.database import get_db
from api.users import user_models

log = logging.getLogger(__name__)


def get_anthropic_api_key(request: Request) -> str:
    """
    Get the Anthropic API key from the request scope.

    This retrieves the key attached during authentication without any database lookups.

    Args:
        request: The FastAPI request object

    Returns:
        The Anthropic API key string

    Raises:
        HTTPException: If the API key is not found in the request scope
    """
    api_key = request.scope.get("anthropic_api_key")
    if not api_key:
        raise HTTPException(status_code=401, detail="API key not found in request context")
    return str(api_key)


def validate_anthropic_api_key(api_key: str) -> bool:
    """
    Validate that an Anthropic API key is functional by making a test request.

    Uses the models API endpoint which is free and doesn't consume any credits.

    Args:
        api_key: The Anthropic API key to validate

    Returns:
        True if the API key is valid and functional, False otherwise
    """
    try:
        client = anthropic.Anthropic(api_key=api_key)
        client.models.list()
        return True
    except anthropic.AuthenticationError:
        return False
    except Exception as e:
        log.exception(f"Failed to validate Anthropic API key: {str(e)}")
        raise HTTPException(status_code=500) from e


async def auth_middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """
    Authentication middleware that validates API keys for all requests.

    Extracts and validates the Anthropic API key from the Authorization header,
    attaches it to request.scope along with the user_id, and rejects requests
    without a valid API key.

    Skips authentication for CORS preflight (OPTIONS) requests.
    """
    # Skip auth check for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        request.scope["user_id"] = UUID("00000000-0000-0000-0000-000000000000")
        request.scope["anthropic_api_key"] = ""
        return await call_next(request)

    # Skip auth check for non-API paths (frontend static files, health checks, etc.)
    if not request.url.path.startswith("/api/"):
        request.scope["user_id"] = UUID("00000000-0000-0000-0000-000000000000")
        request.scope["anthropic_api_key"] = ""
        return await call_next(request)

    authorization = request.headers.get("authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required (Anthropic API key)")

    # Extract API key from "Bearer <key>" format or use as-is
    api_key = authorization.removeprefix("Bearer ").strip()

    if not api_key or not api_key.startswith("sk-ant-"):
        raise HTTPException(status_code=401, detail="Invalid Anthropic API key format")

    # Hash the API key for secure lookup
    anthropic_api_key_sha256 = safe_hash(api_key)

    # First, check if user exists
    with get_db() as db:
        user = (
            db.query(user_models.User)
            .filter(user_models.User.anthropic_api_key_sha256 == anthropic_api_key_sha256)
            .one_or_none()
        )

        if user:
            # User exists, verify hash match
            if not compare_hash_values(user.anthropic_api_key_sha256, anthropic_api_key_sha256):
                raise HTTPException(status_code=404, detail="API key does not match any known user")
            # Attach user_id and API key to request scope for downstream access
            request.scope["user_id"] = user.id
            request.scope["anthropic_api_key"] = api_key
            return await call_next(request)

    # User doesn't exist - validate the API key before creating
    if not validate_anthropic_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid or non-functional Anthropic API key")

    # Create new user
    with get_db() as db:
        user = user_models.User(anthropic_api_key_sha256=anthropic_api_key_sha256)
        db.add(user)
        db.commit()
        db.refresh(user)
        # Attach user_id and API key to request scope for downstream access
        request.scope["user_id"] = user.id
        request.scope["anthropic_api_key"] = api_key
        return await call_next(request)


def get_current_user_id(request: Request) -> UUID:
    """
    Extract user_id from request scope (set by auth_middleware).

    This is a thin wrapper for use with FastAPI's Depends() for backwards compatibility.
    The middleware ensures the user_id is always set for authenticated requests.
    """
    user_id = request.scope.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="User not authenticated")

    if isinstance(user_id, UUID):
        return user_id
    return UUID(user_id)


def safe_hash(value: str) -> str:
    """
    Return a secure sha256 of the input value, salted and hashed with the API secret.
    """
    return hmac.new(_api_secret(), value.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def compare_hash_values(hash1: str, hash2: str) -> bool:
    """
    Return True if two hash values are equal.
    Uses hmac.compare_digest for safe comparison.
    """
    return hmac.compare_digest(hash1, hash2)


def _api_secret() -> bytes:
    api_secret = os.getenv("API_SECRET")
    if not api_secret:
        raise ValueError("Missing required environment variable: API_SECRET")
    return api_secret.strip().encode("utf-8")
