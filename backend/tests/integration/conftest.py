import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.core.config import get_settings
from app.main import app
from app.repositories.dynamodb import clear_table_cache


@pytest.fixture
def table():
    """A fresh, moto-mocked DynamoDB table with the production key schema."""
    with mock_aws():
        clear_table_cache()
        settings = get_settings()
        resource = boto3.resource("dynamodb", region_name=settings.aws_region)
        created = resource.create_table(
            TableName=settings.table_name,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        yield created
        clear_table_cache()


@pytest.fixture
def client(table):
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def as_user(user_id: str) -> dict[str, str]:
    return {"X-Dev-User-Id": user_id}


ALICE = as_user("alice")
BOB = as_user("bob")


def run_payload(day: str = "2026-10-20", **overrides) -> dict:
    body = {"type": "run", "date": day, "duration_min": 45, "rpe": 6, "distance_km": 8.5}
    body.update(overrides)
    return body
