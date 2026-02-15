"""Protocols (interfaces) for the service layer.

Use these as type hints to depend on abstractions, not concrete classes.
"""

from __future__ import annotations

from typing import Protocol

from app.schemas.image import ImageCreateRequest, ImageUploadRequest


class ImageServiceProtocol(Protocol):
    """Interface that any image service must satisfy."""

    def generate_upload_url(self, data: ImageUploadRequest) -> dict:
        """Return a presigned upload response dict (key, bucket, url)."""
        ...

    def create(self, data: ImageCreateRequest) -> dict:
        """Persist image metadata and return the created record."""
        ...

    def get(self, image_id: str) -> dict | None: ...

    def list_images(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> dict: ...

    def delete(self, image_id: str) -> None: ...
