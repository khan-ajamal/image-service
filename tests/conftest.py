"""Shared pytest fixtures for the image-service test suite."""

from flask import Flask
from flask.testing import FlaskClient
import pytest

from app import create_app
from app.config import Settings
from app.services.image_service import ImageService
from tests.repositories.in_memory_db import InMemoryImageRepository
from tests.repositories.s3 import FakeStorageRepository


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
def repository() -> InMemoryImageRepository:
    """Return a fresh in-memory repository."""
    return InMemoryImageRepository()


@pytest.fixture()
def storage() -> FakeStorageRepository:
    """Return a fake storage backend."""
    return FakeStorageRepository(bucket="test-bucket")


@pytest.fixture()
def image_service(
    repository: InMemoryImageRepository,
    storage: FakeStorageRepository,
) -> ImageService:
    """Return an ImageService wired to in-memory repo + fake storage."""
    return ImageService(repository=repository, storage=storage, bucket="test-bucket")


@pytest.fixture()
def app(test_settings: Settings, image_service: ImageService) -> Flask:
    """Create a Flask app configured for testing.

    The concrete ``image_service`` fixture is injected into the factory
    so routes resolve the same instance used by unit tests.
    """
    application = create_app(settings=test_settings, image_service=image_service)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """Return a Flask test client."""
    return app.test_client()
