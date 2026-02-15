"""Protocols (interfaces) for the repository layer.

Use these as type hints to depend on abstractions, not concrete classes.
Swap implementations for testing, different storage backends, etc.
"""

from __future__ import annotations

from typing import Protocol

from app.schemas.image import ImageListResponse, ImageMetadata, PresignedUploadResponse


class ImageRepositoryProtocol(Protocol):
    """Interface that any image repository must satisfy."""

    def save(self, metadata: ImageMetadata) -> None: ...

    def find_by_id(self, image_id: str) -> ImageMetadata | None: ...

    def list_all(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> ImageListResponse: ...

    def delete(self, image_id: str) -> None: ...


class StorageRepositoryProtocol(Protocol):
    """Interface for object-storage operations (S3, MinIO, etc.)."""

    def generate_presigned_upload_url(
        self, key: str, content_type: str, bucket: str | None = None
    ) -> PresignedUploadResponse: ...

    def generate_presigned_download_url(
        self, key: str, bucket: str | None = None
    ) -> str: ...

    def object_exists(self, key: str, bucket: str | None = None) -> bool: ...

    def delete_object(self, key: str, bucket: str | None = None) -> None: ...
