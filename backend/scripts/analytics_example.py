"""Print the analytics summary for the documented worked example.

Run from the backend/ folder:  python -m scripts.analytics_example
Compare the output with the hand calculation in docs/analytics.md.
"""

import json
from dataclasses import asdict

from app.domain.analytics import compute_summary
from app.domain.models import Goal
from tests.unit.test_analytics import AS_OF, worked_example_checkins, worked_example_workouts


def main() -> None:
    summary = compute_summary(
        worked_example_workouts(), worked_example_checkins(), Goal.ENDURANCE, AS_OF
    )
    print(json.dumps(asdict(summary), indent=2, default=str))


if __name__ == "__main__":
    main()
