"""Daily check-in endpoint."""

from tests.integration.conftest import ALICE


def test_put_creates_checkin(client) -> None:
    response = client.put(
        "/v1/checkins/2026-10-20", json={"sleep_hours": 7.5, "fatigue": 3}, headers=ALICE
    )
    assert response.status_code == 200
    body = response.json()
    assert (body["date"], body["sleep_hours"], body["fatigue"], body["soreness"]) == (
        "2026-10-20",
        7.5,
        3,
        None,
    )


def test_put_replaces_the_whole_checkin(client, table) -> None:
    client.put("/v1/checkins/2026-10-20", json={"sleep_hours": 7.5, "fatigue": 3}, headers=ALICE)
    client.put("/v1/checkins/2026-10-20", json={"soreness": 2}, headers=ALICE)

    item = table.get_item(Key={"PK": "USER#alice", "SK": "CHECKIN#2026-10-20"})["Item"]
    assert item["soreness"] == 2
    assert "sleep_hours" not in item and "fatigue" not in item  # PUT = full replacement


def test_empty_checkin_is_rejected(client) -> None:
    response = client.put("/v1/checkins/2026-10-20", json={}, headers=ALICE)
    assert response.status_code == 422


def test_out_of_range_values_are_rejected(client) -> None:
    response = client.put("/v1/checkins/2026-10-20", json={"fatigue": 6}, headers=ALICE)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "fatigue"


def test_invalid_and_future_dates_are_rejected(client) -> None:
    assert (
        client.put("/v1/checkins/2026-02-30", json={"fatigue": 2}, headers=ALICE).status_code == 422
    )
    future = client.put("/v1/checkins/2099-01-01", json={"fatigue": 2}, headers=ALICE)
    assert future.status_code == 422
    assert future.json()["error"]["details"][0]["field"] == "checkin_date"
