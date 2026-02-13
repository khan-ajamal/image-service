"""Image resource endpoints."""

from flask import Blueprint, jsonify

images_bp = Blueprint("images", __name__, url_prefix="/images")


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
