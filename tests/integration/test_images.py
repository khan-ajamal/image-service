"""Integration tests — full CRUD flow against LocalStack.

Requires LocalStack running: docker compose up -d
Run with: pytest tests/integration/ -v
"""

import boto3


LOCALSTACK_ENDPOINT = "http://localhost:4566"
REGION = "ap-south-1"
BUCKET = "image-service-local"


class TestUploadFlow:
    """POST /images/upload — presigned URL generation."""

    def test_upload_returns_presigned_url(self, client):
        resp = client.post(
            "/images/upload",
            json={"filename": "cat photo.png", "content_type": "image/png"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "url" in data
        assert "key" in data
        assert data["bucket"] == BUCKET
        assert data["key"].endswith(".png")

    def test_upload_rejects_non_image(self, client):
        resp = client.post(
            "/images/upload",
            json={"filename": "file.pdf", "content_type": "application/pdf"},
        )
        assert resp.status_code == 422


class TestCreateImage:
    """POST /images — create record after uploading to S3."""

    def _upload_to_s3(self, key: str, content_type: str = "image/png") -> None:
        """Put a fake object directly into LocalStack S3."""
        s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
        s3.put_object(
            Bucket=BUCKET, Key=key, Body=b"fake-image", ContentType=content_type
        )

    def test_create_returns_201(self, client):
        key = "2026/02/13/14/30/01JTEST-cat-photo.png"
        self._upload_to_s3(key)

        resp = client.post(
            "/images",
            json={
                "name": "Cat Photo",
                "category": "pets",
                "content_type": "image/png",
                "user_id": "user-1",
                "image": {"key": key, "bucket": BUCKET},
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "Cat Photo"
        assert data["category"] == "pets"
        assert data["user_id"] == "user-1"
        assert data["s3_key"] == key
        assert "image_id" in data

    def test_create_fails_without_upload(self, client):
        resp = client.post(
            "/images",
            json={
                "name": "Missing",
                "category": "none",
                "content_type": "image/png",
                "user_id": "user-1",
                "image": {"key": "does/not/exist.png", "bucket": BUCKET},
            },
        )
        assert resp.status_code == 400

    def test_create_rejects_invalid_body(self, client):
        resp = client.post("/images", json={"name": "nope"})
        assert resp.status_code == 422


class TestGetImage:
    """GET /images/<image_id> — fetch metadata with download URL."""

    def _create_image(self, client) -> dict:
        key = "2026/02/13/14/30/01JTEST-landscape.jpg"
        s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"data", ContentType="image/jpeg")
        resp = client.post(
            "/images",
            json={
                "name": "Landscape",
                "category": "nature",
                "content_type": "image/jpeg",
                "user_id": "user-2",
                "image": {"key": key, "bucket": BUCKET},
            },
        )
        return resp.get_json()

    def test_get_returns_metadata_with_url(self, client):
        created = self._create_image(client)
        image_id = created["image_id"]

        resp = client.get(f"/images/{image_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["image_id"] == image_id
        assert data["name"] == "Landscape"
        assert "url" in data
        assert data["url"].startswith("http")

    def test_get_nonexistent_returns_404(self, client):
        resp = client.get("/images/nonexistent-id")
        assert resp.status_code == 404


class TestListImages:
    """GET /images — list with filters."""

    def _create_image(self, client, name, category, user_id, suffix="img.png"):
        key = f"2026/02/13/14/30/01JTEST-{suffix}"
        s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"data", ContentType="image/png")
        return client.post(
            "/images",
            json={
                "name": name,
                "category": category,
                "content_type": "image/png",
                "user_id": user_id,
                "image": {"key": key, "bucket": BUCKET},
            },
        ).get_json()

    def test_list_returns_items(self, client):
        self._create_image(client, "A", "pets", "user-1", "a.png")
        self._create_image(client, "B", "nature", "user-2", "b.png")

        resp = client.get("/images")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["items"]) == 2

    def test_list_filter_by_category(self, client):
        self._create_image(client, "A", "pets", "user-1", "a.png")
        self._create_image(client, "B", "nature", "user-2", "b.png")

        resp = client.get("/images?category=pets")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert all(item["category"] == "pets" for item in items)

    def test_list_filter_by_user_id(self, client):
        self._create_image(client, "A", "pets", "user-1", "a.png")
        self._create_image(client, "B", "nature", "user-2", "b.png")

        resp = client.get("/images?user_id=user-1")
        assert resp.status_code == 200
        items = resp.get_json()["items"]
        assert all(item["user_id"] == "user-1" for item in items)

    def test_list_empty(self, client):
        resp = client.get("/images")
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []


class TestDeleteImage:
    """DELETE /images/<image_id> — removes DB record and S3 object."""

    def _create_image(self, client) -> tuple[dict, str]:
        key = "2026/02/13/14/30/01JTEST-delete-me.png"
        s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"data", ContentType="image/png")
        data = client.post(
            "/images",
            json={
                "name": "Delete Me",
                "category": "temp",
                "content_type": "image/png",
                "user_id": "user-1",
                "image": {"key": key, "bucket": BUCKET},
            },
        ).get_json()
        return data, key

    def test_delete_returns_204(self, client):
        created, _ = self._create_image(client)
        resp = client.delete(f"/images/{created['image_id']}")
        assert resp.status_code == 204

    def test_delete_removes_db_record(self, client):
        created, _ = self._create_image(client)
        client.delete(f"/images/{created['image_id']}")

        resp = client.get(f"/images/{created['image_id']}")
        assert resp.status_code == 404

    def test_delete_removes_s3_object(self, client):
        created, key = self._create_image(client)
        client.delete(f"/images/{created['image_id']}")

        s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
        resp = s3.list_objects_v2(Bucket=BUCKET, Prefix=key)
        assert resp.get("KeyCount", 0) == 0

    def test_delete_nonexistent_returns_204(self, client):
        resp = client.delete("/images/nonexistent-id")
        assert resp.status_code == 204
