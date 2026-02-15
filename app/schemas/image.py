"""Pydantic schemas for image requests and responses."""

from pydantic import BaseModel, Field

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
    }
)


class ImageUploadRequest(BaseModel):
    """Schema for the image upload (presigned-URL) request body."""

    filename: str = Field(
        ..., min_length=1, max_length=255, description="Original filename"
    )
    content_type: str = Field(
        ..., pattern=r"^image/", description="MIME type (must start with image/)"
    )


class S3ObjectRef(BaseModel):
    """Reference to an uploaded S3 object, as returned by the upload endpoint."""

    key: str = Field(
        ..., min_length=1, description="S3 object key returned by the upload endpoint"
    )
    bucket: str = Field(
        ..., min_length=1, description="S3 bucket name returned by the upload endpoint"
    )


class ImageCreateRequest(BaseModel):
    """Schema for creating an image record after the file is uploaded to S3."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the image"
    )
    category: str = Field(
        ..., min_length=1, max_length=100, description="Image category"
    )
    content_type: str = Field(
        ..., pattern=r"^image/", description="MIME type (must start with image/)"
    )
    user_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID of the user creating the image",
    )
    image: S3ObjectRef = Field(
        ..., description="S3 object reference returned by the upload endpoint"
    )


class PresignedUploadResponse(BaseModel):
    """Schema for the presigned-URL upload response."""

    key: str = Field(..., description="S3 object key")
    bucket: str = Field(..., description="S3 bucket name")
    url: str = Field(..., description="Presigned PUT URL")


class ImageMetadata(BaseModel):
    """Schema representing stored image metadata."""

    image_id: str
    user_id: str
    name: str
    filename: str
    content_type: str
    category: str
    s3_bucket: str
    s3_key: str
    url: str | None = None
    created_at: str | None = None


class ImageListItem(BaseModel):
    """Summary fields returned in list responses."""

    image_id: str
    user_id: str
    name: str
    category: str
    content_type: str
    created_at: str | None = None


class ImageListResponse(BaseModel):
    """Paginated list of images."""

    items: list[ImageListItem] = []
    next_cursor: str | None = None


class ImageListRequest(BaseModel):
    """Query parameters for paginated image listing."""

    limit: int = Field(20, ge=1, le=100, description="Page size")
    cursor: str | None = Field(None, description="Pagination cursor")
    category: str | None = Field(None, description="Filter by category")
    user_id: str | None = Field(None, description="Filter by user ID")
