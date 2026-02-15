from app.schemas.image import PresignedUploadResponse


class FakeStorageRepository:
    """In-memory substitute for S3StorageRepository."""

    def __init__(self, bucket: str = "test-bucket") -> None:
        self._bucket = bucket
        self._objects: set[str] = set()

    def generate_presigned_upload_url(
        self, key: str, content_type: str, bucket: str | None = None
    ) -> PresignedUploadResponse:
        resolved_bucket = bucket or self._bucket
        return PresignedUploadResponse(
            key=key,
            bucket=resolved_bucket,
            url=f"https://{resolved_bucket}.s3.amazonaws.com/{key}?X-Amz-Signature=fake",
        )

    def put_object(self, key: str) -> None:
        """Simulate a successful upload by recording the key."""
        self._objects.add(key)

    def object_exists(self, key: str, bucket: str | None = None) -> bool:
        return key in self._objects

    def delete_object(self, key: str, bucket: str | None = None) -> None:
        self._objects.discard(key)

    def generate_presigned_download_url(
        self, key: str, bucket: str | None = None
    ) -> str:
        resolved_bucket = bucket or self._bucket
        return f"https://{resolved_bucket}.s3.amazonaws.com/{key}?X-Amz-Signature=fake-download"
