from datetime import date

from app.domain.ids import make_workout_id, new_ulid, parse_workout_id


def test_ulid_is_26_crockford_chars_and_time_ordered() -> None:
    earlier = new_ulid(1_000, bytes(10))
    later = new_ulid(2_000, bytes(10))
    assert len(earlier) == 26
    assert set(earlier) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert earlier < later


def test_workout_id_round_trips() -> None:
    ulid = new_ulid()
    workout_id = make_workout_id(date(2026, 10, 27), ulid)
    assert parse_workout_id(workout_id) == (date(2026, 10, 27), ulid)


def test_malformed_ids_are_rejected() -> None:
    for bad in [
        "",
        "2026-10-27",
        "2026-10-27_short",
        "2026-02-30_" + "0" * 26,
        "2026-10-27_" + "I" * 26,
        "../../etc_" + "0" * 26,
    ]:
        assert parse_workout_id(bad) is None
