"""Unit tests for ImageService."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from tests.repositories.in_memory_db import InMemoryImageRepository
from app.schemas.image import ImageCreateRequest, ImageUploadRequest
from app.services.image_service import ImageService
from tests.conftest import FakeStorageRepository


class TestGenerateUploadUrl:
    def test_returns_presigned_url_response(self, image_service: ImageService):
        result = image_service.generate_upload_url(
            ImageUploadRequest(filename="cat.png", content_type="image/png")
        )
        assert "key" in result
        assert "bucket" in result
        assert "url" in result
        assert result["bucket"] == "test-bucket"
        assert result["key"].endswith("cat.png")

    def test_key_contains_date_prefix(self, image_service: ImageService):
        fixed_now = datetime(2026, 2, 14, 14, 30, 0, tzinfo=UTC)
        with patch("app.services.image_service.datetime") as mock_dt:
            mock_dt.now.return_value = fixed_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = image_service.generate_upload_url(
                ImageUploadRequest(filename="cat.png", content_type="image/png")
            )

        assert result["key"].startswith("2026/02/14/14/30/")
        assert result["key"].endswith("-cat.png")

    def test_slugifies_filename(self, image_service: ImageService):
        result = image_service.generate_upload_url(
            ImageUploadRequest(
                filename="My Vacation Photo (2).PNG",
                content_type="image/png",
            )
        )
        assert result["key"].endswith("-my-vacation-photo-2.png")

    def test_does_not_persist_metadata(self, image_service: ImageService):
        image_service.generate_upload_url(
            ImageUploadRequest(filename="cat.png", content_type="image/png")
        )
        assert image_service.list_images()["items"] == []

    def test_rejects_unsupported_content_type(self, image_service: ImageService):
        with pytest.raises(Exception, match="Unsupported content type"):
            image_service.generate_upload_url(
                ImageUploadRequest(filename="doc.pdf", content_type="image/x-unknown")
            )


class TestCreate:
    def test_create_returns_metadata(self, image_service: ImageService, storage):
        storage.put_object("/2026/02/14/14/30/cat.png")
        result = image_service.create(
            ImageCreateRequest(
                name="My Cat",
                category="pets",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/cat.png", "bucket": "test-bucket"},
            )
        )
        assert result["name"] == "My Cat"
        assert result["category"] == "pets"
        assert result["content_type"] == "image/png"
        assert result["s3_key"] == "/2026/02/14/14/30/cat.png"
        assert result["s3_bucket"] == "test-bucket"
        assert result["user_id"] == "user-1"
        assert result["filename"] == "cat.png"
        assert "image_id" in result
        assert "created_at" in result

    def test_create_persists_to_repository(self, repository: InMemoryImageRepository):
        storage = FakeStorageRepository()
        storage.put_object("/2026/02/14/14/30/dog.jpg")
        svc = ImageService(repository=repository, storage=storage, bucket="test-bucket")
        svc.create(
            ImageCreateRequest(
                name="Dog Pic",
                category="pets",
                content_type="image/jpeg",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/dog.jpg", "bucket": "test-bucket"},
            )
        )

        items = repository.list_all().items
        assert len(items) == 1
        assert items[0].name == "Dog Pic"
        assert items[0].category == "pets"

    def test_create_rejects_unsupported_content_type(self, image_service: ImageService):
        with pytest.raises(Exception, match="Unsupported content type"):
            image_service.create(
                ImageCreateRequest(
                    name="Bad",
                    category="test",
                    content_type="image/x-unknown",
                    user_id="user-1",
                    image={"key": "/2026/02/14/14/30/bad.xyz", "bucket": "test-bucket"},
                )
            )

    def test_create_rejects_when_file_not_uploaded(self, image_service: ImageService):
        with pytest.raises(Exception, match="File not found in storage"):
            image_service.create(
                ImageCreateRequest(
                    name="Ghost",
                    category="test",
                    content_type="image/png",
                    user_id="user-1",
                    image={
                        "key": "/2026/02/14/14/30/ghost.png",
                        "bucket": "test-bucket",
                    },
                )
            )


class TestImageServiceGet:
    def test_get_existing_image_includes_url(
        self, image_service: ImageService, storage
    ):
        storage.put_object("/2026/02/14/14/30/img.png")
        image_service.create(
            ImageCreateRequest(
                name="Img",
                category="test",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/img.png", "bucket": "test-bucket"},
            )
        )
        items = image_service.list_images()["items"]
        result = image_service.get(items[0]["image_id"])
        assert result is not None
        assert "url" in result
        assert "img.png" in result["url"]
        assert result["name"] == "Img"
        assert result["s3_key"] == "/2026/02/14/14/30/img.png"

    def test_get_nonexistent_returns_none(self, image_service: ImageService):
        assert image_service.get("nonexistent-id") is None


class TestImageServiceDelete:
    def test_delete_removes_image_and_s3_object(
        self, image_service: ImageService, storage
    ):
        storage.put_object("/2026/02/14/14/30/del.png")
        image_service.create(
            ImageCreateRequest(
                name="Del",
                category="test",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/del.png", "bucket": "test-bucket"},
            )
        )
        items = image_service.list_images()["items"]
        image_id = items[0]["image_id"]

        # Verify S3 object exists before delete
        assert storage.object_exists("/2026/02/14/14/30/del.png") is True

        image_service.delete(image_id)

        # DB record removed
        assert image_service.get(image_id) is None
        # S3 object removed
        assert storage.object_exists("/2026/02/14/14/30/del.png") is False

    def test_delete_nonexistent_does_not_raise(self, image_service: ImageService):
        image_service.delete("nonexistent-id")  # should not raise


class TestImageServiceList:
    def test_list_empty(self, image_service: ImageService):
        result = image_service.list_images()
        assert result["items"] == []

    def test_list_returns_created_images(self, image_service: ImageService, storage):
        storage.put_object("/2026/02/14/14/30/a.png")
        image_service.create(
            ImageCreateRequest(
                name="A",
                category="c",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/a.png", "bucket": "test-bucket"},
            )
        )
        storage.put_object("/2026/02/14/14/30/b.png")
        image_service.create(
            ImageCreateRequest(
                name="B",
                category="c",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/b.png", "bucket": "test-bucket"},
            )
        )

        result = image_service.list_images()
        assert len(result["items"]) == 2

    def test_list_filters_by_category(self, image_service: ImageService, storage):
        storage.put_object("/2026/02/14/14/30/a.png")
        image_service.create(
            ImageCreateRequest(
                name="A",
                category="pets",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/a.png", "bucket": "test-bucket"},
            )
        )
        storage.put_object("/2026/02/14/14/30/b.jpg")
        image_service.create(
            ImageCreateRequest(
                name="B",
                category="travel",
                content_type="image/jpeg",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/b.jpg", "bucket": "test-bucket"},
            )
        )

        result = image_service.list_images(category="pets")
        assert len(result["items"]) == 1
        assert result["items"][0]["category"] == "pets"

    def test_list_filters_by_user_id(self, image_service: ImageService, storage):
        storage.put_object("/2026/02/14/14/30/a.png")
        image_service.create(
            ImageCreateRequest(
                name="A",
                category="c",
                content_type="image/png",
                user_id="user-1",
                image={"key": "/2026/02/14/14/30/a.png", "bucket": "test-bucket"},
            )
        )
        storage.put_object("/2026/02/14/14/30/b.jpg")
        image_service.create(
            ImageCreateRequest(
                name="B",
                category="c",
                content_type="image/jpeg",
                user_id="user-2",
                image={"key": "/2026/02/14/14/30/b.jpg", "bucket": "test-bucket"},
            )
        )

        result = image_service.list_images(user_id="user-1")
        assert len(result["items"]) == 1
        assert result["items"][0]["user_id"] == "user-1"
