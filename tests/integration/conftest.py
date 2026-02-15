"""Shared fixtures for integration tests using LocalStack.

Start LocalStack before running:  docker compose up -d
"""

import boto3
import pytest

from app import create_app
from app.config import Settings

LOCALSTACK_ENDPOINT = "http://localhost:4566"
REGION = "ap-south-1"
BUCKET = "image-service-local"
TABLE = "images"


def pytest_collection_modifyitems(items):
    """Auto-apply the *integration* marker to every test in this directory."""
    for item in items:
        if "/integration/" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def localstack_settings() -> Settings:
    """Settings wired to LocalStack."""
    return Settings(
        debug=True,
        environment="testing",
        log_level="DEBUG",
        aws_region=REGION,
        aws_endpoint_url=LOCALSTACK_ENDPOINT,
        s3_bucket=BUCKET,
        dynamodb_table=TABLE,
    )


@pytest.fixture(scope="session")
def _localstack_healthcheck():
    """Fail fast if LocalStack is not reachable."""
    import urllib.request

    try:
        urllib.request.urlopen(f"{LOCALSTACK_ENDPOINT}/_localstack/health", timeout=3)
    except Exception:
        pytest.skip("LocalStack is not running — start it with: docker compose up -d")


@pytest.fixture(scope="session")
def integration_app(_localstack_healthcheck, localstack_settings):
    """Create a Flask app connected to LocalStack (session-scoped)."""
    application = create_app(settings=localstack_settings)
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(integration_app):
    """Flask test client for integration tests."""
    return integration_app.test_client()


@pytest.fixture(autouse=True)
def _clean_dynamodb(_localstack_healthcheck):
    """Wipe the DynamoDB table between tests for isolation."""
    resource = boto3.resource(
        "dynamodb", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT
    )
    table = resource.Table(TABLE)

    # Scan all items and delete them
    response = table.scan(ProjectionExpression="user_id, image_id")
    with table.batch_writer() as batch:
        for item in response.get("Items", []):
            batch.delete_item(
                Key={"user_id": item["user_id"], "image_id": item["image_id"]}
            )


@pytest.fixture(autouse=True)
def _clean_s3(_localstack_healthcheck):
    """Empty the S3 bucket between tests for isolation."""
    s3 = boto3.client("s3", region_name=REGION, endpoint_url=LOCALSTACK_ENDPOINT)
    response = s3.list_objects_v2(Bucket=BUCKET)
    objects = response.get("Contents", [])
    if objects:
        s3.delete_objects(
            Bucket=BUCKET,
            Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
        )
