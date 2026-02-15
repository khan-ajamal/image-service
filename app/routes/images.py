"""Image resource endpoints."""

from flask import Blueprint, current_app, jsonify, request

from app.schemas.image import ImageCreateRequest, ImageUploadRequest
from app.services.protocols import ImageServiceProtocol

images_bp = Blueprint("images", __name__, url_prefix="/images")


def _get_image_service() -> ImageServiceProtocol:
    """Resolve the image service registered in the app factory."""
    return current_app.config["IMAGE_SERVICE"]


@images_bp.post("/upload")
def request_upload_url():
    """Return a presigned S3 PUT URL for the client to upload an image.

    Request body::

        {"filename": "photo.png", "content_type": "image/png"}

    Response (201)::

        {"key": "/2026/02/13/14/30/photo.png", "bucket": "my-bucket", "url": "https://..."}
    """
    body = ImageUploadRequest.model_validate(request.get_json(force=True))
    image_service = _get_image_service()
    presigned = image_service.generate_upload_url(body)
    return jsonify(presigned), 201


@images_bp.post("/")
def create_image():
    """Create an image record after the file has been uploaded to S3.

    Request body::

        {
            "name": "My photo",
            "category": "vacation",
            "content_type": "image/png",
            "image": {"key": "/2026/02/13/14/30/photo.png", "bucket": "my-bucket"}
        }

    Response (201)::

        {"image_id": "...", "name": "My photo", ...}
    """
    body = ImageCreateRequest.model_validate(request.get_json(force=True))
    result = _get_image_service().create(body)
    return jsonify(result), 201


@images_bp.get("/<image_id>")
def get_image(image_id: str):
    """Retrieve image metadata by ID."""
    result = _get_image_service().get(image_id)
    if result is None:
        return jsonify({"error": "Image not found"}), 404
    return jsonify(result), 200


@images_bp.get("/")
def list_images():
    """List images with optional pagination and filters."""
    limit = request.args.get("limit", 20, type=int)
    cursor = request.args.get("cursor", None)
    category = request.args.get("category", None)
    user_id = request.args.get("user_id", None)
    result = _get_image_service().list_images(
        limit=limit,
        cursor=cursor,
        category=category,
        user_id=user_id,
    )
    return jsonify(result), 200


@images_bp.delete("/<image_id>")
def delete_image(image_id: str):
    """Delete an image by ID."""
    _get_image_service().delete(image_id)
    return "", 204
