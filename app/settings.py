from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_env(path: Path) -> dict[str, str]:
    """Read a small KEY=VALUE env file."""

    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def _get(values: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key, values.get(key, default))


@dataclass(frozen=True)
class Settings:
    """Application configuration."""

    # Application / data
    app_env: str = "local"
    backend: str = "sqlite"
    knowledge_dir: Path = ROOT / "knowledge"
    sqlite_path: Path = ROOT / "local_data" / "reservation_analytics.db"

    # Required LLM / RAG
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    # Data platform
    data_region: str = "local"
    data_cluster: str = "local"
    data_database: str = "reservation_analytics"

    # Athena
    athena_workgroup: str = "primary"
    athena_output_location: str = "s3://change-me/athena-results/"

    # Internal SQL Gateway
    sql_gateway_endpoint: str | None = None
    sql_gateway_user_id: str | None = None
    sql_gateway_token: str | None = None

    @property
    def aws_region(self) -> str:
        return self.data_region

    @property
    def athena_database(self) -> str:
        return self.data_database

    def require_llm(self) -> None:
        """Fail clearly instead of switching to a second rule-based pipeline."""

        if not self.openai_api_key:
            raise RuntimeError(
                "LLM service is unavailable: OPENAI_API_KEY is not configured."
            )


def load_settings(env_file: str = "config/local.env") -> Settings:
    values = _read_env(ROOT / env_file)
    values.update(_read_env(ROOT / ".env"))

    return Settings(
        app_env=_get(values, "APP_ENV", "local"),
        backend=_get(values, "DATA_BACKEND", "sqlite").lower(),
        knowledge_dir=ROOT / _get(values, "KNOWLEDGE_DIR", "knowledge"),
        sqlite_path=ROOT / _get(
            values,
            "SQLITE_PATH",
            "local_data/reservation_analytics.db",
        ),
        openai_api_key=_get(values, "OPENAI_API_KEY") or None,
        openai_model=_get(values, "OPENAI_MODEL", "gpt-4.1-mini"),
        embedding_model=_get(
            values,
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        data_region=_get(values, "DATA_REGION", "local"),
        data_cluster=_get(values, "DATA_CLUSTER", "local"),
        data_database=_get(values, "DATA_DATABASE", "reservation_analytics"),
        athena_workgroup=_get(values, "ATHENA_WORKGROUP", "primary"),
        athena_output_location=_get(
            values,
            "ATHENA_OUTPUT_LOCATION",
            "s3://change-me/athena-results/",
        ),
        sql_gateway_endpoint=_get(values, "SQL_GATEWAY_ENDPOINT") or None,
        sql_gateway_user_id=_get(values, "SQL_GATEWAY_USER_ID") or None,
        sql_gateway_token=_get(values, "SQL_GATEWAY_TOKEN") or None,
    )
