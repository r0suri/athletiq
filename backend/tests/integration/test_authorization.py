"""Authentication and cross-user isolation."""

from tests.integration.conftest import ALICE, BOB, run_payload


def test_missing_dev_user_header_returns_401(client) -> None:
    response = client.post("/v1/workouts", json=run_payload())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_malformed_dev_user_header_returns_401(client) -> None:
    response = client.get("/v1/workouts", headers={"X-Dev-User-Id": "alice#USER#bob"})
    assert response.status_code == 401


def test_other_user_cannot_read_a_workout(client) -> None:
    workout = client.post("/v1/workouts", json=run_payload(), headers=ALICE).json()

    response = client.get(f"/v1/workouts/{workout['id']}", headers=BOB)

    assert response.status_code == 404  # 404, not 403: never confirm it exists
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_other_user_cannot_delete_a_workout(client) -> None:
    workout = client.post("/v1/workouts", json=run_payload(), headers=ALICE).json()

    assert client.delete(f"/v1/workouts/{workout['id']}", headers=BOB).status_code == 404
    assert client.get(f"/v1/workouts/{workout['id']}", headers=ALICE).status_code == 200


def test_list_only_returns_own_workouts(client) -> None:
    client.post("/v1/workouts", json=run_payload("2026-10-20"), headers=ALICE)
    mine = client.post("/v1/workouts", json=run_payload("2026-10-21"), headers=BOB).json()

    listed = client.get("/v1/workouts?from=2026-10-01&to=2026-10-31", headers=BOB).json()

    assert [w["id"] for w in listed["items"]] == [mine["id"]]


def test_reusing_another_users_cursor_cannot_reach_their_data(client) -> None:
    for day in range(1, 6):
        client.post("/v1/workouts", json=run_payload(f"2026-10-{day:02d}"), headers=ALICE)
    alice_page = client.get(
        "/v1/workouts?from=2026-10-01&to=2026-10-31&limit=2", headers=ALICE
    ).json()

    bob_page = client.get(
        f"/v1/workouts?from=2026-10-01&to=2026-10-31&cursor={alice_page['next_cursor']}",
        headers=BOB,
    )

    assert bob_page.status_code == 200
    assert bob_page.json()["items"] == []  # the cursor only carries a sort key


def test_checkins_are_isolated_per_user(client, table) -> None:
    client.put("/v1/checkins/2026-10-20", json={"fatigue": 5}, headers=ALICE)
    client.put("/v1/checkins/2026-10-20", json={"fatigue": 1}, headers=BOB)

    alice = table.get_item(Key={"PK": "USER#alice", "SK": "CHECKIN#2026-10-20"})["Item"]
    bob = table.get_item(Key={"PK": "USER#bob", "SK": "CHECKIN#2026-10-20"})["Item"]
    assert (alice["fatigue"], bob["fatigue"]) == (5, 1)
