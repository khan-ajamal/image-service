"""Application factory for the image-service Flask app."""

from __future__ import annotations

from flask import Flask

from app.config import Settings
from app.routes import register_blueprints
from app.errors import register_error_handlers
from app.services.protocols import ImageServiceProtocol


def create_app(
    settings: Settings | None = None,
    *,
    image_service: ImageServiceProtocol | None = None,
) -> Flask:
    """Create and configure the Flask application.

    Args:
        settings: Optional Settings instance. If not provided, settings are
                  loaded from environment variables.

    Returns:
        Configured Flask application.
    """
    app = Flask(__name__)

    # Load configuration
    if settings is None:
        settings = Settings()

    app.config.from_mapping(settings.as_flask_config())
    app.config["SETTINGS"] = settings

    if image_service is None:
        from app.services.image_service import ImageService
        from app.repositories.s3 import S3StorageRepository
        from app.repositories.dynamodb import DynamoDBImageRepository

        image_service = ImageService(
            repository=DynamoDBImageRepository(
                table_name=settings.dynamodb_table,
                region=settings.aws_region,
            ),
            storage=S3StorageRepository(
                bucket=settings.s3_bucket,
                region=settings.aws_region,
            ),
            bucket=settings.s3_bucket,
        )

    app.config["IMAGE_SERVICE"] = image_service

    # Initialize error handlers and routes
    register_error_handlers(app)
    register_blueprints(app)

    return app
