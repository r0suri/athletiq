"""Application configuration loaded from environment variables.

All configuration flows through this one typed object so that the rest of the
code never reads os.environ directly. Locally the defaults are used; in AWS the
values come from the Lambda environment defined in template.yaml.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_ENVS = ("local", "test")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "dev", "prod"] = "local"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    # "cognito": identity comes from JWT claims already verified by API Gateway.
    # "local":   identity comes from an X-Dev-User-Id header. Development only.
    auth_mode: Literal["cognito", "local"] = "cognito"

    table_name: str = "athletiq-local"
    aws_region: str = "us-east-1"
    dynamodb_endpoint_url: str | None = None  # e.g. a local moto server

    @field_validator("dynamodb_endpoint_url", mode="before")
    @classmethod
    def _blank_endpoint_means_aws(cls, value: object) -> object:
        # DYNAMODB_ENDPOINT_URL="" explicitly means "use real AWS endpoints".
        return None if value == "" else value

    @model_validator(mode="after")
    def _forbid_local_auth_outside_local_envs(self) -> "Settings":
        if self.auth_mode != "local":
            return self
        if self.app_env not in LOCAL_ENVS:
            raise ValueError(f"AUTH_MODE=local is not allowed when APP_ENV={self.app_env}")
        if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            # Defence in depth: refuse even if APP_ENV was misconfigured inside Lambda.
            raise ValueError("AUTH_MODE=local is not allowed inside AWS Lambda")
        return self

    @property
    def docs_enabled(self) -> bool:
        # Interactive API docs are a local-development convenience only.
        return self.app_env in LOCAL_ENVS


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env vars once per container)."""
    return Settings()
