"""Profile endpoints: defaults, validation and isolation."""

from tests.integration.conftest import ALICE, BOB


def test_missing_profile_returns_defaults_without_creating_one(client, table) -> None:
    response = client.get("/v1/me/profile", headers=ALICE)

    assert response.status_code == 200
    assert response.json() == {
        "goal": "general_fitness",
        "timezone": "UTC",
        "configured": False,
        "updated_at": None,
    }
    assert "Item" not in table.get_item(Key={"PK": "USER#alice", "SK": "PROFILE"})


def test_put_then_get_profile(client) -> None:
    body = {"goal": "endurance", "timezone": "America/Los_Angeles"}
    saved = client.put("/v1/me/profile", json=body, headers=ALICE)
    assert saved.status_code == 200
    assert saved.json()["configured"] is True

    fetched = client.get("/v1/me/profile", headers=ALICE).json()
    assert (fetched["goal"], fetched["timezone"], fetched["configured"]) == (
        "endurance",
        "America/Los_Angeles",
        True,
    )


def test_put_replaces_profile(client) -> None:
    client.put("/v1/me/profile", json={"goal": "endurance", "timezone": "UTC"}, headers=ALICE)
    client.put("/v1/me/profile", json={"goal": "strength", "timezone": "Asia/Tokyo"}, headers=ALICE)
    fetched = client.get("/v1/me/profile", headers=ALICE).json()
    assert (fetched["goal"], fetched["timezone"]) == ("strength", "Asia/Tokyo")


def test_invalid_timezones_are_rejected(client) -> None:
    for bad in ["Mars/Olympus_Mons", "", "../../etc/passwd", "PST8PDT-ish", "utc "]:
        response = client.put(
            "/v1/me/profile", json={"goal": "strength", "timezone": bad}, headers=ALICE
        )
        assert response.status_code == 422, bad
        assert response.json()["error"]["details"][0]["field"] == "timezone"


def test_invalid_goal_and_unknown_fields_are_rejected(client) -> None:
    bad_goal = client.put("/v1/me/profile", json={"goal": "bulk", "timezone": "UTC"}, headers=ALICE)
    assert bad_goal.status_code == 422
    extra = client.put(
        "/v1/me/profile",
        json={"goal": "strength", "timezone": "UTC", "user_id": "bob"},
        headers=ALICE,
    )
    assert extra.status_code == 422


def test_profiles_are_isolated_per_user(client) -> None:
    client.put("/v1/me/profile", json={"goal": "strength", "timezone": "Asia/Tokyo"}, headers=ALICE)

    bob = client.get("/v1/me/profile", headers=BOB).json()

    assert bob["configured"] is False
    assert bob["timezone"] == "UTC"


def test_profile_requires_authentication(client) -> None:
    response = client.get("/v1/me/profile")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
