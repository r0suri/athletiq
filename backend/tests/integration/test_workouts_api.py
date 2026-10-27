"""Workout endpoints against a moto-mocked DynamoDB table."""

from tests.integration.conftest import ALICE, run_payload


def create(client, headers, body) -> dict:
    response = client.post("/v1/workouts", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def test_create_run_returns_201_with_load_and_location(client) -> None:
    response = client.post("/v1/workouts", json=run_payload(), headers=ALICE)

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "run"
    assert body["load"] == 270  # 45 min x RPE 6
    assert body["distance_km"] == 8.5
    assert body["source"] == "manual"
    assert body["id"].startswith("2026-10-20_")
    assert response.headers["location"] == f"/v1/workouts/{body['id']}"
    assert response.headers["x-request-id"]


def test_create_strength_with_exercises(client) -> None:
    body = {
        "type": "strength",
        "date": "2026-10-21",
        "duration_min": 50,
        "rpe": 7,
        "exercises": [{"name": "Back squat", "sets": 5, "reps": 5, "weight_kg": 100}],
    }
    created = create(client, ALICE, body)
    assert created["load"] == 350
    assert created["distance_km"] is None
    assert created["exercises"] == [
        {"name": "Back squat", "sets": 5, "reps": 5, "weight_kg": 100.0}
    ]


def test_get_returns_the_stored_workout(client) -> None:
    created = create(client, ALICE, run_payload(notes="easy tempo"))

    response = client.get(f"/v1/workouts/{created['id']}", headers=ALICE)

    assert response.status_code == 200
    assert response.json() == created


def test_delete_then_get_returns_404(client) -> None:
    created = create(client, ALICE, run_payload())

    assert client.delete(f"/v1/workouts/{created['id']}", headers=ALICE).status_code == 204
    assert client.get(f"/v1/workouts/{created['id']}", headers=ALICE).status_code == 404
    second = client.delete(f"/v1/workouts/{created['id']}", headers=ALICE)
    assert second.status_code == 404
    assert second.json()["error"]["code"] == "NOT_FOUND"


def test_malformed_id_returns_404(client) -> None:
    response = client.get("/v1/workouts/not-a-real-id", headers=ALICE)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_list_is_newest_first_and_filtered_by_date_range(client) -> None:
    for day in ["2026-10-01", "2026-10-15", "2026-10-20", "2026-10-25"]:
        create(client, ALICE, run_payload(day))

    response = client.get("/v1/workouts?from=2026-10-10&to=2026-10-24", headers=ALICE)

    assert response.status_code == 200
    assert [w["date"] for w in response.json()["items"]] == ["2026-10-20", "2026-10-15"]
    assert response.json()["next_cursor"] is None


def test_multiple_workouts_same_day_are_all_listed(client) -> None:
    ids = {create(client, ALICE, run_payload("2026-10-20"))["id"] for _ in range(3)}
    listed = client.get("/v1/workouts?from=2026-10-20&to=2026-10-20", headers=ALICE).json()
    assert {w["id"] for w in listed["items"]} == ids


def test_list_filters_by_type(client) -> None:
    create(client, ALICE, run_payload("2026-10-20"))
    create(client, ALICE, {"type": "ride", "date": "2026-10-21", "duration_min": 60, "rpe": 5})
    create(client, ALICE, run_payload("2026-10-22"))

    response = client.get("/v1/workouts?from=2026-10-01&to=2026-10-31&type=ride", headers=ALICE)

    assert [w["type"] for w in response.json()["items"]] == ["ride"]


def test_pagination_returns_every_item_exactly_once(client) -> None:
    created = {
        create(client, ALICE, run_payload(f"2026-10-{day:02d}"))["id"] for day in range(1, 8)
    }

    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        url = "/v1/workouts?from=2026-10-01&to=2026-10-31&limit=3"
        if cursor:
            url += f"&cursor={cursor}"
        page = client.get(url, headers=ALICE).json()
        seen += [w["id"] for w in page["items"]]
        pages += 1
        cursor = page["next_cursor"]
        if not cursor:
            break

    assert pages == 3  # 3 + 3 + 1
    assert len(seen) == len(set(seen)) == 7
    assert set(seen) == created


def test_paginated_type_filter_collects_full_pages(client) -> None:
    for day in range(1, 11):
        kind = "ride" if day % 2 else "run"
        create(
            client,
            ALICE,
            {"type": kind, "date": f"2026-10-{day:02d}", "duration_min": 30, "rpe": 4},
        )

    page = client.get(
        "/v1/workouts?from=2026-10-01&to=2026-10-31&type=run&limit=3", headers=ALICE
    ).json()

    assert [w["date"] for w in page["items"]] == ["2026-10-10", "2026-10-08", "2026-10-06"]
    assert page["next_cursor"] is not None


def test_invalid_cursor_is_rejected(client) -> None:
    response = client.get("/v1/workouts?cursor=%%%garbage", headers=ALICE)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "cursor"


def test_from_after_to_is_rejected(client) -> None:
    response = client.get("/v1/workouts?from=2026-10-20&to=2026-10-01", headers=ALICE)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Validation and the error envelope
# ---------------------------------------------------------------------------
def _assert_validation_error(response, field: str) -> None:
    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["request_id"]
    assert field in [d["field"] for d in error["details"]], error["details"]


def test_rpe_out_of_range_is_rejected(client) -> None:
    response = client.post("/v1/workouts", json=run_payload(rpe=11), headers=ALICE)
    _assert_validation_error(response, "rpe")


def test_zero_duration_is_rejected(client) -> None:
    response = client.post("/v1/workouts", json=run_payload(duration_min=0), headers=ALICE)
    _assert_validation_error(response, "duration_min")


def test_future_date_is_rejected(client) -> None:
    response = client.post("/v1/workouts", json=run_payload("2099-01-01"), headers=ALICE)
    _assert_validation_error(response, "date")


def test_unknown_type_is_rejected(client) -> None:
    response = client.post("/v1/workouts", json=run_payload(type="swim"), headers=ALICE)
    assert response.status_code == 422


def test_run_cannot_carry_exercises(client) -> None:
    body = run_payload(exercises=[{"name": "squat", "sets": 1, "reps": 1}])
    _assert_validation_error(client.post("/v1/workouts", json=body, headers=ALICE), "exercises")


def test_client_cannot_set_user_id(client) -> None:
    body = run_payload(user_id="bob")
    _assert_validation_error(client.post("/v1/workouts", json=body, headers=ALICE), "user_id")


def test_unknown_route_uses_error_envelope(client) -> None:
    response = client.get("/v1/nope", headers=ALICE)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
