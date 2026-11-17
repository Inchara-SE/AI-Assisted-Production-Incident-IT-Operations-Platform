"""Application configuration loaded from environment variables via pydantic-settings."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """OpsPilot application settings.

    Values are read from environment variables.  A ``.env`` file in the project
    root is loaded automatically when present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_ENV: str = "local"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_LOG_LEVEL: str = "INFO"
    APP_SECRET_KEY: str = "replace-with-random-secret-for-local-development"

    # ── JWT Authentication ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "replace-with-random-jwt-secret-for-local-development"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # ── Database — Application ───────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+psycopg://opspilot_app:app_local_password@localhost:5432/opspilot"
    )

    # ── Database — Migrator (Alembic) ────────────────────────────────────
    DATABASE_URL_MIGRATOR: str = (
        "postgresql+psycopg://opspilot_migrator:migrator_local_password@localhost:5432/opspilot"
    )

    # ── LLM Provider ────────────────────────────────────────────────────
    LLM_PROVIDER: str = "mock"
    LLM_API_KEY: str = ""

    # ── Correlation ─────────────────────────────────────────────────────
    CORRELATION_WINDOW_MINUTES: int = 15

    # ── Metadata / payload limits ───────────────────────────────────────
    MAX_METADATA_KEYS: int = 20
    MAX_METADATA_DEPTH: int = 2
    MAX_MESSAGE_LENGTH: int = 1000
    MAX_REQUEST_SIZE_BYTES: int = 65536


# Module-level singleton, lazily instantiated on first import.
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    global _settings  # noqa: PLW0603
    if _settings is None:
        _settings = Settings()
    return _settings
