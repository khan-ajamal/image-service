"""Blueprint registration."""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Import and register all route blueprints."""
    from app.routes.images import images_bp

    app.register_blueprint(images_bp)
