"""FastAPI v1 auth dependency — Supabase JWT verification."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_security = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_security)],
) -> dict:
    """Verify Supabase JWT. Raises 401 if invalid or missing."""
    from supabase import create_client  # lazy import: only need Supabase at auth time

    token = credentials.credentials
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Auth service not configured",
        )
    client = create_client(url, key)
    result = client.auth.get_user(token)
    if not result or not result.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": result.user.id, "email": result.user.email}


CurrentUser = Annotated[dict, Depends(get_current_user)]
