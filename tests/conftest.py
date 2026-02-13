"""Shared pytest fixtures for the image-service test suite."""

import pytest

from app import create_app
from app.config import Settings


@pytest.fixture()
def test_settings() -> Settings:
    """Return Settings tuned for testing."""
    return Settings(
        debug=True,
        environment="testing",
        log_level="DEBUG",
        s3_bucket="test-bucket",
    )


@pytest.fixture()
def app(test_settings: Settings):
    """Create a Flask app configured for testing.

    The concrete ``image_service`` fixture is injected into the factory
    so routes resolve the same instance used by unit tests.
    """
    application = create_app(settings=test_settings)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    """Return a Flask test client."""
    return app.test_client()
