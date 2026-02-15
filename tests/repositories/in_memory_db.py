"""InMemory implementation of ImageRepositoryProtocol."""

from __future__ import annotations

import logging

from app.schemas.image import ImageListItem, ImageListResponse, ImageMetadata

logger = logging.getLogger(__name__)


class InMemoryImageRepository:
    """In-memory image repository."""

    def __init__(self) -> None:
        self._store: dict[str, ImageMetadata] = {}

    def save(self, metadata: ImageMetadata) -> None:
        """Persist image metadata."""
        self._store[metadata.image_id] = metadata

    def find_by_id(self, image_id: str) -> ImageMetadata | None:
        return self._store.get(image_id)

    def list_all(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> ImageListResponse:
        """Return a paginated list of images."""
        items = list(self._store.values())

        if category:
            items = [m for m in items if m.category == category]
        if user_id:
            items = [m for m in items if m.user_id == user_id]

        if cursor:
            # Find starting index after the cursor
            idx = next((i for i, m in enumerate(items) if m.image_id == cursor), None)
            if idx is not None:
                items = items[idx + 1 :]

        page = items[:limit]
        list_items = [
            ImageListItem(**m.model_dump(include=ImageListItem.model_fields.keys()))
            for m in page
        ]
        next_cursor = page[-1].image_id if len(page) == limit else None
        return ImageListResponse(items=list_items, next_cursor=next_cursor)

    def delete(self, image_id: str) -> None:
        """Remove image metadata by ID."""
        self._store.pop(image_id, None)
