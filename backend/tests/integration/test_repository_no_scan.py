"""Guard rail: no repository operation may ever Scan the table."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.repositories.checkins import CheckInRepository
from app.repositories.workouts import WorkoutRepository
from tests.integration.conftest import ALICE, run_payload


@pytest.fixture
def forbid_scan(table):
    table.scan = MagicMock(side_effect=AssertionError("Scan is not allowed"))
    return table


def test_workout_operations_never_scan(client, forbid_scan) -> None:
    workout = client.post("/v1/workouts", json=run_payload(), headers=ALICE).json()
    repo = WorkoutRepository(forbid_scan)

    repo.get("alice", workout["id"])
    repo.list_page("alice", date(2026, 10, 1), date(2026, 10, 31), limit=10)
    list(repo.iter_range("alice", date(2026, 10, 1), date(2026, 10, 31)))
    repo.delete("alice", workout["id"])
    list(CheckInRepository(forbid_scan).iter_range("alice", date(2026, 10, 1), date(2026, 10, 31)))

    forbid_scan.scan.assert_not_called()


def test_iter_range_returns_workouts_oldest_first(client, table) -> None:
    for day in ["2026-10-20", "2026-10-05", "2026-10-12"]:
        client.post("/v1/workouts", json=run_payload(day), headers=ALICE)

    dates = [
        w.record.workout_date.isoformat()
        for w in WorkoutRepository(table).iter_range("alice", date(2026, 10, 1), date(2026, 10, 31))
    ]

    assert dates == ["2026-10-05", "2026-10-12", "2026-10-20"]
