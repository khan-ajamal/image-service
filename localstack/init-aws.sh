#!/bin/bash
set -euo pipefail

echo "Initialising LocalStack resources..."

REGION="ap-south-1"
BUCKET="image-service-local"
TABLE="images"

# --- S3 ---
awslocal s3 mb "s3://${BUCKET}" --region "${REGION}"
echo "Created S3 bucket: ${BUCKET}"

# --- DynamoDB ---
awslocal dynamodb create-table \
  --table-name "${TABLE}" \
  --attribute-definitions \
    AttributeName=user_id,AttributeType=S \
    AttributeName=image_id,AttributeType=S \
    AttributeName=category,AttributeType=S \
  --key-schema \
    AttributeName=user_id,KeyType=HASH \
    AttributeName=image_id,KeyType=RANGE \
  --global-secondary-indexes \
    '[
      {
        "IndexName": "image_id-index",
        "KeySchema": [{"AttributeName":"image_id","KeyType":"HASH"}],
        "Projection": {"ProjectionType":"ALL"}
      },
      {
        "IndexName": "category-index",
        "KeySchema": [
          {"AttributeName":"category","KeyType":"HASH"},
          {"AttributeName":"image_id","KeyType":"RANGE"}
        ],
        "Projection": {"ProjectionType":"ALL"}
      }
    ]' \
  --billing-mode PAY_PER_REQUEST \
  --region "${REGION}"
echo "Created DynamoDB table: ${TABLE}"

echo "LocalStack init complete."
