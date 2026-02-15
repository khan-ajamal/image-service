"""DynamoDB image repository — data-access layer.

Implements ``ImageRepositoryProtocol`` using an AWS DynamoDB table.
"""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource


from app.schemas.image import ImageListItem, ImageListResponse, ImageMetadata

logger = logging.getLogger(__name__)


class DynamoDBImageRepository:
    """DynamoDB-backed image repository."""

    def __init__(
        self,
        table_name: str,
        region: str = "ap-south-1",
        dynamodb_resource: DynamoDBServiceResource | None = None,
    ) -> None:
        self._resource = dynamodb_resource or boto3.resource(
            "dynamodb", region_name=region
        )
        self._table = self._resource.Table(table_name)

    def save(self, metadata: ImageMetadata) -> None:
        """Persist image metadata as a DynamoDB item."""
        logger.info("Saving image %s to DynamoDB", metadata.image_id)
        self._table.put_item(Item=metadata.model_dump())

    def find_by_id(self, image_id: str) -> ImageMetadata | None:
        """Return image metadata or ``None`` if not found."""
        try:
            response = self._table.get_item(Key={"image_id": image_id})
        except ClientError:
            logger.exception("Error fetching image %s", image_id)
            raise

        item = response.get("Item")
        if item is None:
            return None
        return ImageMetadata.model_validate(item)

    def list_all(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> ImageListResponse:
        """Return a paginated list of images using DynamoDB ``scan``.

        Pagination uses ``ExclusiveStartKey`` / ``LastEvaluatedKey``.
        The *cursor* is the ``image_id`` of the last item from the
        previous page.
        """
        scan_kwargs: dict[str, Any] = {"Limit": limit}

        if cursor:
            scan_kwargs["ExclusiveStartKey"] = {"image_id": cursor}

        # Build optional FilterExpression
        filter_parts: list[str] = []
        expr_values: dict[str, str] = {}
        expr_names: dict[str, str] = {}

        if category:
            filter_parts.append("category = :cat")
            expr_values[":cat"] = category

        if user_id:
            filter_parts.append("user_id = :uid")
            expr_values[":uid"] = user_id

        if filter_parts:
            scan_kwargs["FilterExpression"] = " AND ".join(filter_parts)
            scan_kwargs["ExpressionAttributeValues"] = expr_values
            if expr_names:
                scan_kwargs["ExpressionAttributeNames"] = expr_names

        response = self._table.scan(**scan_kwargs)

        items = [
            ImageListItem.model_validate(item) for item in response.get("Items", [])
        ]

        next_cursor: str | None = None
        last_key = response.get("LastEvaluatedKey")
        if last_key:
            next_cursor = last_key["image_id"]

        return ImageListResponse(items=items, next_cursor=next_cursor)

    def delete(self, image_id: str) -> None:
        """Remove an image item from DynamoDB."""
        logger.info("Deleting image %s from DynamoDB", image_id)
        self._table.delete_item(Key={"image_id": image_id})
