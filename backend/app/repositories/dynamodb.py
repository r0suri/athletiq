"""DynamoDB connection and type conversion helpers.

Single-table design (see docs/architecture): every item for a user shares
PK = "USER#<sub>", and the sort key encodes the entity type and date, e.g.
    WORKOUT#2026-10-27#<ULID>      CHECKIN#2026-10-27
Every read is a GetItem or a Query on one partition: the repositories never Scan.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Any

import boto3

from app.core.config import Settings


@lru_cache
def _table(table_name: str, region: str, endpoint_url: str | None) -> Any:
    # Cached per Lambda container: creating the resource is relatively slow.
    resource = boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url)
    return resource.Table(table_name)


def get_table(settings: Settings) -> Any:
    return _table(settings.table_name, settings.aws_region, settings.dynamodb_endpoint_url)


def clear_table_cache() -> None:
    _table.cache_clear()


def user_pk(user_id: str) -> str:
    return f"USER#{user_id}"


def to_dynamo(value: Any) -> Any:
    """DynamoDB rejects Python floats; store numbers as Decimal (via str to avoid noise)."""
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: to_dynamo(v) for k, v in value.items() if v is not None}
    if isinstance(value, list | tuple):
        return [to_dynamo(v) for v in value]
    return value


def from_dynamo(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: from_dynamo(v) for k, v in value.items()}
    if isinstance(value, list):
        return [from_dynamo(v) for v in value]
    return value
