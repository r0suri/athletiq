"""Unexpected failures return the error envelope without leaking internals."""

from fastapi.testclient import TestClient

from app.api.dependencies import get_workout_service
from app.main import app
from tests.integration.conftest import ALICE


class ExplodingService:
    def get(self, user_id: str, workout_id: str):
        raise RuntimeError("connection string with secrets")


def test_unhandled_error_returns_generic_500(table) -> None:
    app.dependency_overrides[get_workout_service] = lambda: ExplodingService()
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get(
                "/v1/workouts/2026-10-20_01JB7Q8Z1T3XK9V2M4N6P8R0SA", headers=ALICE
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "INTERNAL_ERROR"
    assert "secrets" not in response.text
    assert error["request_id"]
