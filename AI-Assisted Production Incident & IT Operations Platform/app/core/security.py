"""Authentication helpers: Argon2id password hashing, JWT token creation / validation,
and FastAPI dependencies for extracting the current user and enforcing roles."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import argon2
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db

# ── Password hashing (Argon2id) ─────────────────────────────────────────────

_hasher = argon2.PasswordHasher(
    time_cost=2,
    memory_cost=19_456,
    parallelism=1,
    type=argon2.Type.ID,
)


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches *hashed*.

    Also re-hashes transparently when the stored hash uses outdated parameters.
    """
    try:
        return _hasher.verify(hashed, plain)
    except argon2.exceptions.VerifyMismatchError:
        return False
    except argon2.exceptions.VerificationError:
        return False


def needs_rehash(hashed: str) -> bool:
    """Return ``True`` when the hash should be updated to current parameters."""
    return _hasher.check_needs_rehash(hashed)


# ── JWT helpers ──────────────────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    user_id: UUID,
    roles: list[str],
    settings: Settings | None = None,
) -> str:
    """Create a signed JWT access token encoding user identity and roles."""
    if settings is None:
        settings = get_settings()

    now = datetime.now(tz=timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "roles": roles,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> dict:
    """Decode and validate a JWT token.  Raises ``HTTPException`` on failure."""
    if settings is None:
        settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("sub") is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim.",
            )
        return payload
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc


# ── FastAPI dependencies ─────────────────────────────────────────────────────


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Extract and validate the current authenticated user from the bearer token.

    Returns a dict with ``user_id`` (UUID) and ``roles`` (list[str]).
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
        )

    payload = decode_access_token(credentials.credentials, settings)

    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )

    # Verify user still exists and is active.
    from app.models.user import User

    user = db.query(User).filter(User.id == UUID(user_id_str)).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive.",
        )

    return {
        "user_id": UUID(user_id_str),
        "roles": payload.get("roles", []),
    }


def require_role(*allowed_roles: str):
    """Return a FastAPI dependency that checks the current user has one of *allowed_roles*.

    Usage::

        @router.post("/...", dependencies=[Depends(require_role("admin"))])
        def protected_endpoint(...): ...

    Or inject directly::

        current_user: dict = Depends(require_role("admin", "on_call_engineer"))
    """

    def _role_checker(
        current_user: Annotated[dict, Depends(get_current_user)],
    ) -> dict:
        user_roles: list[str] = current_user.get("roles", [])
        if not any(r in allowed_roles for r in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )
        return current_user

    return _role_checker
