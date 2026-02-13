"""Application configuration using pydantic-settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Prefix all env vars with ``IMAGE_SERVICE_`` (e.g. ``IMAGE_SERVICE_DEBUG=true``).
    """

    model_config = SettingsConfigDict(
        env_prefix="IMAGE_SERVICE_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    secret_key: str = "super-secret-key"
    app_name: str = "image-service"
    debug: bool = False
    environment: str = Field(
        default="production", description="production | staging | development"
    )
    log_level: str = "INFO"

    # AWS
    aws_region: str = "ap-south-1"
    aws_endpoint_url: str | None = None
    s3_bucket: str = ""
    dynamodb_table: str = "images"

    def as_flask_config(self) -> dict:
        """Return a dict suitable for ``app.config.from_mapping()``."""
        return {
            "DEBUG": self.debug,
            "TESTING": False,
            "ENV": self.environment,
            "SECRET_KEY": self.secret_key,
        }
