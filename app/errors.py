"""Global error handlers for the Flask app."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from flask import jsonify
from pydantic import ValidationError

if TYPE_CHECKING:
    from flask import Flask

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base application error with an HTTP status code."""

    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundError(AppError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class BadRequestError(AppError):
    """Client sent an invalid request."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, status_code=400)


def register_error_handlers(app: Flask) -> None:
    """Register JSON error handlers on the Flask app."""

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        logger.warning("AppError: %s", error.message)
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        logger.warning("Validation error: %s", error)
        return jsonify({"error": "Validation error", "details": error.errors()}), 422

    @app.errorhandler(400)
    def handle_bad_request(error):
        return jsonify({"error": getattr(error, "description", "Bad request")}), 400

    @app.errorhandler(404)
    def handle_not_found(_error):
        return jsonify({"error": "Not found"}), 404

    @app.errorhandler(500)
    def handle_internal(_error):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error"}), 500
