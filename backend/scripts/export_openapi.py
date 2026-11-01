"""Write the API's OpenAPI schema to a file (the frontend generates types from it).

Usage (from backend/):  python -m scripts.export_openapi ../frontend/src/api/openapi.json
"""

import json
import os
import sys
from pathlib import Path

# The schema is the same in every environment; local settings just let the app import.
os.environ.setdefault("APP_ENV", "local")
os.environ.setdefault("AUTH_MODE", "local")

from app.main import app  # noqa: E402


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
