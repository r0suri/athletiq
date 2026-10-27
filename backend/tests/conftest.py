"""Test-wide environment.

Values are force-set (not setdefault) so tests are hermetic: a developer's
backend/.env or exported shell variables can never change test behaviour.
Environment variables take precedence over the .env file in pydantic-settings.
"""

import os

os.environ["APP_ENV"] = "test"
os.environ["APP_VERSION"] = "0.1.0-test"
os.environ["POWERTOOLS_SERVICE_NAME"] = "athletiq"
os.environ["AUTH_MODE"] = "local"
os.environ["TABLE_NAME"] = "athletiq-test"
os.environ["AWS_REGION"] = "us-east-1"
os.environ["DYNAMODB_ENDPOINT_URL"] = ""  # blank -> default endpoint, intercepted by moto
# Fake credentials so boto3 can never reach a real AWS account from tests.
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ.pop("AWS_PROFILE", None)
os.environ.pop("AWS_LAMBDA_FUNCTION_NAME", None)
