"""Cognito mode, exercised through the real Lambda handler with API Gateway events.

API Gateway verifies the JWT before Lambda runs and passes the verified claims in
requestContext.authorizer.jwt.claims. These tests simulate that event shape.
"""

import json
from dataclasses import dataclass

import pytest

from app.core.config import Settings, get_settings
from app.main import app, handler


@dataclass
class FakeLambdaContext:
    function_name: str = "athletiq-api"
    memory_limit_in_mb: int = 512
    invoked_function_arn: str = "arn:aws:lambda:us-east-1:123456789012:function:athletiq-api"
    aws_request_id: str = "test-request-id"


def api_event(
    method: str, path: str, sub: str | None, body: dict | None = None, headers: dict | None = None
) -> dict:
    request_context: dict = {
        "accountId": "123456789012",
        "apiId": "example",
        "domainName": "example.execute-api.us-east-1.amazonaws.com",
        "http": {
            "method": method,
            "path": path,
            "protocol": "HTTP/1.1",
            "sourceIp": "203.0.113.1",
            "userAgent": "pytest",
        },
        "requestId": f"req-{method}-{sub}",
        "routeKey": f"{method} /v1/{{proxy+}}",
        "stage": "$default",
        "time": "27/Oct/2026:12:00:00 +0000",
        "timeEpoch": 1793102400000,
    }
    if sub is not None:
        request_context["authorizer"] = {"jwt": {"claims": {"sub": sub, "token_use": "access"}}}
    return {
        "version": "2.0",
        "routeKey": request_context["routeKey"],
        "rawPath": path,
        "rawQueryString": "",
        "headers": {
            "host": "example.execute-api.us-east-1.amazonaws.com",
            "content-type": "application/json",
            **(headers or {}),
        },
        "requestContext": request_context,
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


@pytest.fixture
def cognito_mode(table):
    app.dependency_overrides[get_settings] = lambda: Settings(
        auth_mode="cognito", app_env="test", table_name=get_settings().table_name
    )
    yield
    app.dependency_overrides.clear()


def call(event: dict) -> tuple[int, dict]:
    result = handler(event, FakeLambdaContext())
    body = json.loads(result["body"]) if result.get("body") else {}
    return result["statusCode"], body


RUN = {"type": "run", "date": "2026-10-20", "duration_min": 30, "rpe": 5}
USER_A = "3f9c1e2a-0b7d-4c55-9a1e-6d2f8b4c7a10"
USER_B = "8a7b6c5d-4e3f-4a1b-9c8d-7e6f5a4b3c2d"


def test_verified_sub_claim_identifies_the_user(cognito_mode) -> None:
    status, created = call(api_event("POST", "/v1/workouts", USER_A, RUN))
    assert status == 201

    status, fetched = call(api_event("GET", f"/v1/workouts/{created['id']}", USER_A))
    assert status == 200
    assert fetched["id"] == created["id"]


def test_other_cognito_user_gets_404(cognito_mode) -> None:
    _, created = call(api_event("POST", "/v1/workouts", USER_A, RUN))
    status, body = call(api_event("GET", f"/v1/workouts/{created['id']}", USER_B))
    assert status == 404
    assert body["error"]["code"] == "NOT_FOUND"


def test_missing_claims_return_401(cognito_mode) -> None:
    status, body = call(api_event("GET", "/v1/workouts", sub=None))
    assert status == 401
    assert body["error"]["code"] == "UNAUTHORIZED"


def test_dev_header_is_ignored_in_cognito_mode(cognito_mode) -> None:
    # An attacker sending the local-mode header gains nothing in AWS.
    event = api_event("GET", "/v1/workouts", sub=None, headers={"x-dev-user-id": "alice"})
    status, _ = call(event)
    assert status == 401


def test_request_id_comes_from_api_gateway(cognito_mode) -> None:
    status, body = call(api_event("POST", "/v1/workouts", USER_A, {"type": "run"}))
    assert status == 422
    assert body["error"]["request_id"] == f"req-POST-{USER_A}"
