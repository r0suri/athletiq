from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import app, handler

client = TestClient(app)


def test_health_returns_ok_with_version() -> None:
    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "0.1.0-test", "environment": "test"}


def test_unknown_route_returns_404() -> None:
    assert client.get("/v1/does-not-exist").status_code == 404


@dataclass
class FakeLambdaContext:
    function_name: str = "athletiq-api"
    memory_limit_in_mb: int = 512
    invoked_function_arn: str = "arn:aws:lambda:us-east-1:123456789012:function:athletiq-api"
    aws_request_id: str = "test-request-id"


def _http_api_event(path: str) -> dict:
    """Minimal API Gateway HTTP API (payload v2.0) event, as Lambda receives it."""
    return {
        "version": "2.0",
        "routeKey": f"GET {path}",
        "rawPath": path,
        "rawQueryString": "",
        "headers": {"host": "example.execute-api.us-east-1.amazonaws.com"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "example",
            "domainName": "example.execute-api.us-east-1.amazonaws.com",
            "http": {
                "method": "GET",
                "path": path,
                "protocol": "HTTP/1.1",
                "sourceIp": "203.0.113.1",
                "userAgent": "pytest",
            },
            "requestId": "test-correlation-id",
            "routeKey": f"GET {path}",
            "stage": "$default",
            "time": "27/Oct/2026:12:00:00 +0000",
            "timeEpoch": 1793102400000,
        },
        "isBase64Encoded": False,
    }


def test_lambda_handler_serves_health_via_api_gateway_event() -> None:
    """Proves the Mangum adapter wiring works exactly as it will in Lambda."""
    result = handler(_http_api_event("/v1/health"), FakeLambdaContext())

    assert result["statusCode"] == 200
    assert '"status":"ok"' in result["body"]
