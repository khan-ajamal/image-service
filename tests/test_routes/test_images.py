"""Contains tests for image-related API endpoints."""


class TestCreateImage:
    def test_create_returns_201(self, client):
        response = client.post("/images/")
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "Image created"


class TestGetImage:
    def test_get_returns_metadata(self, client):
        response = client.get(f"/images/123")
        assert response.status_code == 200
        data = response.get_json()
        assert data["image_id"] == "123"


class TestListImages:
    def test_list_returns_200(self, client):
        response = client.get("/images/")
        assert response.status_code == 200


class TestDeleteImage:
    def test_delete_returns_204(self, client):
        response = client.delete(f"/images/123")
        assert response.status_code == 204
