"""Unit tests for image route endpoints."""

import json


class TestPresignedUploadUrl:
    def test_returns_200_with_presigned_url(self, client):
        response = client.post(
            "/images/upload",
            data=json.dumps({"filename": "cat.png", "content_type": "image/png"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "key" in data
        assert "bucket" in data
        assert "url" in data
        assert data["key"].endswith("-cat.png")

    def test_invalid_body_returns_422(self, client):
        response = client.post(
            "/images/upload",
            data=json.dumps({"filename": ""}),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_non_image_content_type_returns_422(self, client):
        response = client.post(
            "/images/upload",
            data=json.dumps({"filename": "doc.txt", "content_type": "text/plain"}),
            content_type="application/json",
        )
        assert response.status_code == 422


class TestCreateImage:
    def test_create_returns_201(self, client, storage):
        storage.put_object("2026/02/13/14/30/cat.png")
        response = client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "My Cat",
                    "category": "pets",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {
                        "key": "2026/02/13/14/30/cat.png",
                        "bucket": "test-bucket",
                    },
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["name"] == "My Cat"
        assert data["category"] == "pets"
        assert "image_id" in data

    def test_create_missing_fields_returns_422(self, client):
        response = client.post(
            "/images",
            data=json.dumps({"name": "X"}),
            content_type="application/json",
        )
        assert response.status_code == 422

    def test_create_without_upload_returns_400(self, client):
        response = client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "Ghost",
                    "category": "test",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {
                        "key": "2026/02/13/14/30/ghost.png",
                        "bucket": "test-bucket",
                    },
                }
            ),
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "File not found" in response.get_json()["error"]


class TestGetImage:
    def test_get_nonexistent_returns_404(self, client):
        response = client.get("/images/nonexistent")
        assert response.status_code == 404

    def test_get_returns_metadata_with_url(self, client, storage):
        storage.put_object("2026/02/13/14/30/cat.png")
        post_resp = client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "Cat",
                    "category": "pets",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {
                        "key": "2026/02/13/14/30/cat.png",
                        "bucket": "test-bucket",
                    },
                }
            ),
            content_type="application/json",
        )
        image_id = post_resp.get_json()["image_id"]

        response = client.get(f"/images/{image_id}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["name"] == "Cat"
        assert data["image_id"] == image_id
        assert "url" in data
        assert "cat.png" in data["url"]


class TestListImages:
    def test_list_returns_200(self, client):
        response = client.get("/images")
        assert response.status_code == 200
        data = response.get_json()
        assert "items" in data

    def test_list_filters_by_category(self, client, storage):
        storage.put_object("2026/02/13/14/30/a.png")
        client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "A",
                    "category": "pets",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {"key": "2026/02/13/14/30/a.png", "bucket": "test-bucket"},
                }
            ),
            content_type="application/json",
        )
        storage.put_object("2026/02/13/14/30/b.jpg")
        client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "B",
                    "category": "travel",
                    "content_type": "image/jpeg",
                    "user_id": "user-1",
                    "image": {"key": "2026/02/13/14/30/b.jpg", "bucket": "test-bucket"},
                }
            ),
            content_type="application/json",
        )

        response = client.get("/images?category=pets")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["category"] == "pets"

    def test_list_filters_by_user_id(self, client, storage):
        storage.put_object("2026/02/13/14/30/a.png")
        client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "A",
                    "category": "c",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {"key": "2026/02/13/14/30/a.png", "bucket": "test-bucket"},
                }
            ),
            content_type="application/json",
        )
        storage.put_object("2026/02/13/14/30/b.jpg")
        client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "B",
                    "category": "c",
                    "content_type": "image/jpeg",
                    "user_id": "user-2",
                    "image": {"key": "2026/02/13/14/30/b.jpg", "bucket": "test-bucket"},
                }
            ),
            content_type="application/json",
        )

        response = client.get("/images?user_id=user-1")
        assert response.status_code == 200
        data = response.get_json()
        assert len(data["items"]) == 1
        assert data["items"][0]["user_id"] == "user-1"


class TestDeleteImage:
    def test_delete_returns_204(self, client, storage):
        storage.put_object("2026/02/13/14/30/x.png")
        # Create an image record first
        post_resp = client.post(
            "/images",
            data=json.dumps(
                {
                    "name": "To Delete",
                    "category": "test",
                    "content_type": "image/png",
                    "user_id": "user-1",
                    "image": {
                        "key": "2026/02/13/14/30/x.png",
                        "bucket": "test-bucket",
                    },
                }
            ),
            content_type="application/json",
        )
        assert post_resp.status_code == 201
        image_id = post_resp.get_json()["image_id"]

        response = client.delete(f"/images/{image_id}")
        assert response.status_code == 204
