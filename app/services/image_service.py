from datetime import datetime, UTC

from ulid import ULID

from app.errors import BadRequestError

from app.repositories.protocols import ImageRepositoryProtocol
from app.repositories.protocols import StorageRepositoryProtocol
from app.schemas.image import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    ImageCreateRequest,
    ImageMetadata,
    ImageUploadRequest,
)
from app.utils import slugify_filename


class ImageService:
    """Orchestrates image operations.

    Accepts a repository and a storage backend via constructor injection.
    """

    def __init__(
        self,
        repository: ImageRepositoryProtocol,
        storage: StorageRepositoryProtocol,
        bucket: str,
    ) -> None:
        self._repo = repository
        self._storage = storage
        self._bucket = bucket

    @staticmethod
    def _generate_s3_key(filename: str, now: datetime | None = None) -> str:
        """Build an S3 key with a date-based prefix, ULID, and slugified filename.

        Format: ``/yyyy/mm/dd/HH/MM/<ulid>-<slugified-filename>``

        The ULID component guarantees uniqueness even when two users
        upload a file with the same name at the same moment.
        """
        now = now or datetime.now(UTC)
        slug = slugify_filename(filename)
        unique = str(ULID()).lower()
        prefix = now.strftime("/%Y/%m/%d/%H/%M")
        return f"{prefix}/{unique}-{slug}"

    def generate_upload_url(self, data: ImageUploadRequest) -> dict:
        """Return a presigned S3 PUT URL so the client can upload directly.

        This does **not** create a database record — call :meth:`create`
        after the client finishes uploading.
        """
        if data.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise BadRequestError(
                f"Unsupported content type '{data.content_type}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}"
            )

        s3_key = self._generate_s3_key(data.filename)

        presigned = self._storage.generate_presigned_upload_url(
            key=s3_key,
            content_type=data.content_type,
        )

        return presigned.model_dump()

    def create(self, data: ImageCreateRequest) -> dict:
        """Create an image record after the file has been uploaded to S3.

        Raises :class:`BadRequestError` if the object does not exist in S3.
        """
        if data.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            raise BadRequestError(
                f"Unsupported content type '{data.content_type}'. "
                f"Allowed types: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}"
            )

        if not self._storage.object_exists(data.image.key, bucket=data.image.bucket):
            raise BadRequestError(
                f"File not found in storage for key '{data.image.key}'. "
                "Please upload the file before creating the image record."
            )

        image_id = str(ULID())
        now = datetime.now(UTC)

        metadata = ImageMetadata(
            image_id=image_id,
            user_id=data.user_id,
            name=data.name,
            filename=data.image.key.rsplit("/", 1)[-1],
            content_type=data.content_type,
            category=data.category,
            s3_bucket=data.image.bucket,
            s3_key=data.image.key,
            created_at=now.isoformat(),
        )
        self._repo.save(metadata)
        return metadata.model_dump()

    def get(self, image_id: str) -> dict | None:
        """Return image metadata with a presigned download URL, or ``None``."""
        metadata = self._repo.find_by_id(image_id)
        if metadata is None:
            return None

        url = self._storage.generate_presigned_download_url(
            key=metadata.s3_key, bucket=metadata.s3_bucket
        )
        result = metadata.model_dump()
        result["url"] = url
        return result

    def list_images(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> dict:
        """Return a paginated list of images."""
        result = self._repo.list_all(
            limit=limit,
            cursor=cursor,
            category=category,
            user_id=user_id,
        )
        return result.model_dump()

    def delete(self, image_id: str) -> None:
        """Delete the image record and its S3 object."""
        metadata = self._repo.find_by_id(image_id)
        if metadata is not None:
            self._storage.delete_object(key=metadata.s3_key, bucket=metadata.s3_bucket)
        self._repo.delete(image_id)
