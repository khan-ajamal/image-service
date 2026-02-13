"""Application factory for the image-service Flask app."""

from __future__ import annotations

from flask import Flask

from app.config import Settings
from app.routes import register_blueprints
from app.errors import register_error_handlers


def create_app(settings: Settings | None = None) -> Flask:
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

    # Initialize error handlers and routes
    register_error_handlers(app)
    register_blueprints(app)

    return app
