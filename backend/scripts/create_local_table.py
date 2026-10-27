"""Create the AthletIQ table on a local DynamoDB-compatible endpoint (moto server).

Usage (from backend/, with `moto_server -p 5001` running in another terminal):
    python -m scripts.create_local_table
"""

import boto3

from app.core.config import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.dynamodb_endpoint_url:
        raise SystemExit("Set DYNAMODB_ENDPOINT_URL (e.g. http://127.0.0.1:5001) first.")
    client = boto3.client(
        "dynamodb", region_name=settings.aws_region, endpoint_url=settings.dynamodb_endpoint_url
    )
    if settings.table_name in client.list_tables()["TableNames"]:
        print(f"Table {settings.table_name} already exists.")
        return
    client.create_table(
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
    print(f"Created table {settings.table_name} at {settings.dynamodb_endpoint_url}.")


if __name__ == "__main__":
    main()
