"""Image resource endpoints."""

from flask import Blueprint, current_app, jsonify, request

from app.schemas.image import ImageUploadRequest
from app.services.protocols import ImageServiceProtocol

images_bp = Blueprint("images", __name__, url_prefix="/images")


def _get_image_service() -> ImageServiceProtocol:
    """Resolve the image service registered in the app factory."""
    return current_app.config["IMAGE_SERVICE"]


@images_bp.post("/upload")
def upload_image():
    """Return a presigned S3 PUT URL for the client to upload an image.

    Request body::

        {"filename": "photo.png", "content_type": "image/png"}

    Response (201)::

        {"key": "/2026/02/13/14/30/1234-photo.png", "bucket": "my-bucket", "url": "https://..."}
    """
    body = ImageUploadRequest.model_validate(request.get_json(force=True))
    image_service = _get_image_service()
    presigned = image_service.generate_upload_url(body)
    return jsonify(presigned), 201


@images_bp.post("/")
def create_image():
    return jsonify({"message": "Image created"}), 201


@images_bp.get("/<image_id>")
def get_image(image_id: str):
    """GEt image metadata by ID."""
    return jsonify({"image_id": image_id}), 200


@images_bp.get("/")
def list_images():
    """List images with optional pagination and filters."""
    return jsonify([]), 200


@images_bp.delete("/<image_id>")
def delete_image(image_id: str):
    """Delete an image by ID."""
    return jsonify({"message": "Image deleted"}), 204
