"""S3 storage repository — object-storage layer.

Handles presigned URL generation and other S3 interactions.
"""

from __future__ import annotations

import logging

import boto3
from mypy_boto3_s3.client import S3Client
from botocore.config import Config as BotoConfig


from app.schemas.image import PresignedUploadResponse

logger = logging.getLogger(__name__)

# Default presigned URL expiry: 15 minutes
_DEFAULT_EXPIRY_SECONDS = 900


class S3StorageRepository:
    """AWS S3 storage repository implementation."""

    def __init__(
        self,
        bucket: str,
        region: str = "ap-south-1",
        expiry_seconds: int = _DEFAULT_EXPIRY_SECONDS,
        s3_client: S3Client | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self._bucket = bucket
        self._region = region
        self._expiry_seconds = expiry_seconds

        # Allow injecting a pre-built client (useful for testing / LocalStack).
        # When a custom endpoint is provided (e.g. LocalStack), force
        # path-style addressing so presigned URLs use
        # ``http://host/bucket/key`` instead of ``http://bucket.host/key``.
        boto_config: dict = {"signature_version": "s3v4"}
        if endpoint_url:
            boto_config["s3"] = {"addressing_style": "path"}

        self._client = s3_client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=BotoConfig(**boto_config),
        )

    def generate_presigned_upload_url(
        self, key: str, content_type: str, bucket: str | None = None
    ) -> PresignedUploadResponse:
        """Create a presigned PUT URL so clients can upload directly to S3.

        Args:
            key: S3 object key (e.g. ``2026/02/13/14/30/my-photo.png``).
            content_type: MIME type of the object (e.g. ``image/png``).
            bucket: Optional bucket override. Falls back to instance bucket.

        Returns:
            :class:`PresignedUploadResponse` with *key*, *bucket*, and *url*.
        """
        resolved_bucket = bucket or self._bucket
        logger.info(
            "Generating presigned upload URL for key=%s bucket=%s", key, resolved_bucket
        )

        url = self._client.generate_presigned_url(
            ClientMethod="put_object",
            Params={
                "Bucket": resolved_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=self._expiry_seconds,
        )

        return PresignedUploadResponse(
            key=key,
            bucket=resolved_bucket,
            url=url,
        )

    def object_exists(self, key: str, bucket: str | None = None) -> bool:
        """Check whether an object exists in S3 via ``head_object``."""
        resolved_bucket = bucket or self._bucket
        try:
            self._client.head_object(Bucket=resolved_bucket, Key=key)
            return True
        except self._client.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise

    def generate_presigned_download_url(
        self, key: str, bucket: str | None = None
    ) -> str:
        """Create a presigned GET URL so clients can view/download an object.

        Args:
            key: S3 object key.
            bucket: Optional bucket override. Falls back to instance bucket.

        Returns:
            A presigned GET URL string.
        """
        resolved_bucket = bucket or self._bucket
        logger.info(
            "Generating presigned download URL for key=%s bucket=%s",
            key,
            resolved_bucket,
        )
        return self._client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": resolved_bucket, "Key": key},
            ExpiresIn=self._expiry_seconds,
        )

    def delete_object(self, key: str, bucket: str | None = None) -> None:
        """Delete an object from S3."""
        resolved_bucket = bucket or self._bucket
        logger.info("Deleting object key=%s bucket=%s", key, resolved_bucket)
        self._client.delete_object(Bucket=resolved_bucket, Key=key)
