"""Simple authentication dependency for demo purposes."""

from uuid import UUID

from fastapi import HTTPException, Request


async def get_current_user_id(request: Request) -> UUID:
    """
    Extract and validate user ID from Authorization header.

    For demo purposes, the Authorization header should contain a valid UUID.
    This is NOT secure for production use.

    This dependency extracts the header from the Request object directly
    to avoid polluting the OpenAPI spec with auth requirements.

    Args:
        request: FastAPI Request object

    Returns:
        UUID: The validated user ID

    Raises:
        HTTPException: If header is missing or invalid
    """
    # Skip auth check for OPTIONS requests (CORS preflight)
    if request.method == "OPTIONS":
        return UUID("00000000-0000-0000-0000-000000000000")

    authorization = request.headers.get("authorization")

    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        user_id = UUID(authorization)
        return user_id
    except ValueError as e:
        raise HTTPException(status_code=401, detail="Invalid authorization token (must be a valid UUID)") from e
