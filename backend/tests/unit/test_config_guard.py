"""Local development auth must be impossible to enable in AWS."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


@pytest.mark.parametrize("env", ["dev", "prod"])
def test_local_auth_is_rejected_in_deployed_environments(env) -> None:
    with pytest.raises(ValidationError, match="AUTH_MODE=local is not allowed"):
        Settings(auth_mode="local", app_env=env)


def test_local_auth_is_rejected_inside_lambda_even_if_env_is_misconfigured(monkeypatch) -> None:
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "athletiq-dev-api")
    with pytest.raises(ValidationError, match="inside AWS Lambda"):
        Settings(auth_mode="local", app_env="test")


def test_cognito_auth_is_the_default(monkeypatch) -> None:
    monkeypatch.delenv("AUTH_MODE", raising=False)  # the test suite itself runs in local mode
    assert Settings(_env_file=None, app_env="prod").auth_mode == "cognito"


def test_local_auth_is_allowed_for_local_and_test() -> None:
    assert Settings(auth_mode="local", app_env="local").auth_mode == "local"


def test_blank_endpoint_url_means_real_aws_endpoint() -> None:
    assert Settings(dynamodb_endpoint_url="").dynamodb_endpoint_url is None


def test_tests_ignore_a_developer_env_file(tmp_path, monkeypatch) -> None:
    # A local .env pointing at a moto server must not leak into the test settings.
    (tmp_path / ".env").write_text("DYNAMODB_ENDPOINT_URL=http://127.0.0.1:5001\nAPP_ENV=local\n")
    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.dynamodb_endpoint_url is None
    assert settings.app_env == "test"
