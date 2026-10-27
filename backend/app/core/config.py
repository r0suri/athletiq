"""Application configuration loaded from environment variables.

All configuration flows through this one typed object so that the rest of the
code never reads os.environ directly. Locally the defaults are used; in AWS the
values come from the Lambda environment defined in template.yaml.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["local", "test", "dev", "prod"] = "local"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    table_name: str = "athletiq-local"

    @property
    def docs_enabled(self) -> bool:
        # Interactive API docs are a local-development convenience only.
        return self.app_env in ("local", "test")


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read env vars once per container)."""
    return Settings()
