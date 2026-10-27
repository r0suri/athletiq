from app.services.analytics import round_floats


def test_round_floats_is_half_up_and_recursive() -> None:
    data = {"a": 2.675, "b": [1.005, 3], "c": {"d": None, "e": 4.333333}, "f": 7}
    assert round_floats(data) == {"a": 2.68, "b": [1.01, 3], "c": {"d": None, "e": 4.33}, "f": 7}
