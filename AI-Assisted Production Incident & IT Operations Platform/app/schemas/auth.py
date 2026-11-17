"""Authentication and user schemas."""

from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """User credentials for bearer token acquisition."""
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """JWT bearer token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserResponse(BaseModel):
    """Public user identity schema. password_hash is strictly excluded."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    team_id: UUID | None = None
    roles: list[str] = Field(default_factory=list)
    is_active: bool
