"""DynamoDB image repository — data-access layer.

Implements ``ImageRepositoryProtocol`` using an AWS DynamoDB table.
"""

from __future__ import annotations

import logging
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource

from app.schemas.image import ImageListItem, ImageListResponse, ImageMetadata

logger = logging.getLogger(__name__)

IMAGE_ID_INDEX = "image_id-index"
CATEGORY_INDEX = "category-index"


class DynamoDBImageRepository:
    """DynamoDB-backed image repository."""

    def __init__(
        self,
        table_name: str,
        region: str = "ap-south-1",
        dynamodb_resource: DynamoDBServiceResource | None = None,
        endpoint_url: str | None = None,
    ) -> None:
        self._resource = dynamodb_resource or boto3.resource(
            "dynamodb", region_name=region, endpoint_url=endpoint_url
        )
        self._table = self._resource.Table(table_name)

    @staticmethod
    def _to_item(metadata: ImageMetadata) -> dict[str, Any]:
        """Convert an ``ImageMetadata`` to a DynamoDB item dict."""
        item: dict[str, Any] = {
            "image_id": metadata.image_id,
            "user_id": metadata.user_id,
            "name": metadata.name,
            "filename": metadata.filename,
            "content_type": metadata.content_type,
            "category": metadata.category,
            "s3_bucket": metadata.s3_bucket,
            "s3_key": metadata.s3_key,
        }
        if metadata.url is not None:
            item["url"] = metadata.url
        if metadata.created_at is not None:
            item["created_at"] = metadata.created_at
        return item

    @staticmethod
    def _from_item(item: dict[str, Any]) -> ImageMetadata:
        """Convert a DynamoDB item dict to an ``ImageMetadata``."""
        return ImageMetadata(
            image_id=item["image_id"],
            user_id=item["user_id"],
            name=item["name"],
            filename=item["filename"],
            content_type=item["content_type"],
            category=item["category"],
            s3_bucket=item["s3_bucket"],
            s3_key=item["s3_key"],
            url=item.get("url"),
            created_at=item.get("created_at"),
        )

    @staticmethod
    def _to_list_item(item: dict[str, Any]) -> ImageListItem:
        """Convert a raw DynamoDB item to an ``ImageListItem``."""
        return ImageListItem(
            image_id=item["image_id"],
            user_id=item["user_id"],
            name=item["name"],
            category=item["category"],
            content_type=item["content_type"],
            created_at=item.get("created_at"),
        )

    def save(self, metadata: ImageMetadata) -> None:
        """Persist image metadata as a DynamoDB item."""
        logger.info("Saving image %s to DynamoDB", metadata.image_id)
        self._table.put_item(Item=self._to_item(metadata))

    def find_by_id(self, image_id: str) -> ImageMetadata | None:
        """Look up an image via the ``image_id-index`` GSI.

        Returns metadata or ``None`` if not found.
        """
        try:
            response = self._table.query(
                IndexName=IMAGE_ID_INDEX,
                KeyConditionExpression=Key("image_id").eq(image_id),
                Limit=1,
            )
        except ClientError:
            logger.exception("Error fetching image %s", image_id)
            raise

        items = response.get("Items", [])
        if not items:
            return None
        return self._from_item(items[0])

    def list_all(
        self,
        limit: int = 20,
        cursor: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
    ) -> ImageListResponse:
        """Return a paginated list of images.

        Chooses the most efficient access strategy:
        * ``user_id`` provided → Query the base table (PK)
        * ``category`` provided → Query ``category-index`` GSI
        * ``user_id`` + ``category`` → Query base table, filter on category
        * Neither → Scan
        """
        if user_id:
            return self._query_by_user(
                user_id, limit=limit, cursor=cursor, category=category
            )
        if category:
            return self._query_by_category(category, limit=limit, cursor=cursor)
        return self._scan_all(limit=limit, cursor=cursor)

    def _query_by_user(
        self,
        user_id: str,
        limit: int,
        cursor: str | None = None,
        category: str | None = None,
    ) -> ImageListResponse:
        """Query the base table on ``user_id`` partition."""
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": Key("user_id").eq(user_id),
            "Limit": limit,
        }
        if cursor:
            kwargs["ExclusiveStartKey"] = {"user_id": user_id, "image_id": cursor}
        if category:
            kwargs["FilterExpression"] = "category = :cat"
            kwargs["ExpressionAttributeValues"] = {":cat": category}

        response = self._table.query(**kwargs)
        return self._build_list_response(response)

    def _query_by_category(
        self,
        category: str,
        limit: int,
        cursor: str | None = None,
    ) -> ImageListResponse:
        """Query the ``category-index`` GSI."""
        kwargs: dict[str, Any] = {
            "IndexName": CATEGORY_INDEX,
            "KeyConditionExpression": Key("category").eq(category),
            "Limit": limit,
        }
        if cursor:
            # GSI cursor needs all key attributes of the GSI *and* the base table
            kwargs["ExclusiveStartKey"] = {
                "category": category,
                "image_id": cursor,
            }

        response = self._table.query(**kwargs)
        return self._build_list_response(response)

    def _scan_all(
        self,
        limit: int,
        cursor: str | None = None,
    ) -> ImageListResponse:
        """Fall back to a Scan when no filters are provided."""
        kwargs: dict[str, Any] = {"Limit": limit}
        if cursor:
            # For scan cursor we need the base table key — look up the item.
            metadata = self.find_by_id(cursor)
            if metadata:
                kwargs["ExclusiveStartKey"] = {
                    "user_id": metadata.user_id,
                    "image_id": metadata.image_id,
                }

        response = self._table.scan(**kwargs)
        return self._build_list_response(response)

    def _build_list_response(
        self,
        response: dict[str, Any],
    ) -> ImageListResponse:
        """Build an ``ImageListResponse`` from a DynamoDB query/scan response."""
        items = [self._to_list_item(item) for item in response.get("Items", [])]

        next_cursor: str | None = None
        last_key = response.get("LastEvaluatedKey")
        if last_key:
            next_cursor = last_key["image_id"]

        return ImageListResponse(items=items, next_cursor=next_cursor)

    def delete(self, image_id: str) -> None:
        """Remove an image item from DynamoDB.

        Looks up the item via the ``image_id-index`` GSI to obtain the
        ``user_id`` needed for the composite primary key.
        """
        metadata = self.find_by_id(image_id)
        if metadata is None:
            logger.info("Image %s not found — nothing to delete", image_id)
            return

        logger.info("Deleting image %s from DynamoDB", image_id)
        self._table.delete_item(Key={"user_id": metadata.user_id, "image_id": image_id})
