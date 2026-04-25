"""Application configuration using Pydantic v2 settings management."""

from functools import lru_cache
from typing import Literal

from pydantic import RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "LifePilot"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # API
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Database
    database_url: str = "mysql+aiomysql://root@localhost:3306/lifepilot"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30

    # Redis
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")
    redis_cache_ttl: int = 3600  # 1 hour default TTL

    # Local file storage
    storage_dir: str = "./uploads"

    # S3/R2 Storage (unused – kept for future cloud migration)
    s3_bucket_name: str = "lifepilot-storage"
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_endpoint_url: str | None = None  # For R2 or MinIO

    # Rate Limiting (Requirement 37.1)
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Pagination (Requirement 37.5)
    pagination_default_page_size: int = 20
    pagination_max_page_size: int = 100
    pagination_min_page_size: int = 1

    # Google OAuth (Requirement 1.3)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    # Google Calendar OAuth (Requirement 4.1)
    google_calendar_redirect_uri: str = "http://localhost:8000/api/v1/exams/calendar/callback"

    # SMS Gateway (Requirements 1.4, 1.5, 1.6)
    sms_gateway_url: str = ""
    sms_api_key: str = ""
    otp_validity_seconds: int = 300  # 5 minutes

    # Encryption (Requirement 36.1)
    # Master key for data encryption at rest. Should be a 32-byte base64-encoded key.
    # Generate with: python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
    encryption_master_key: str = "Y2hhbmdlLW1lLWluLXByb2R1Y3Rpb24tMzItYnl0ZXM="  # Change in production!

    # Admin Alerting (Requirement 38.5)
    # Error rate threshold percentage - trigger alert when exceeded
    admin_alert_error_rate_threshold: float = 5.0
    # Minimum requests required before checking error rate
    admin_alert_min_requests: int = 100
    # Time window for error rate calculation (in minutes)
    admin_alert_window_minutes: int = 15
    # Cooldown period between alerts (in minutes)
    admin_alert_cooldown_minutes: int = 30
    # Critical error rate threshold for immediate escalation
    admin_alert_critical_rate_threshold: float = 10.0


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
