from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def _value(values: dict[str, str], key: str, default: str = "") -> str:
    return os.environ.get(key, values.get(key, default))


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    backend: str = "sqlite"
    knowledge_dir: Path = ROOT / "knowledge"

    data_region: str = "local"
    data_cluster: str = "local"
    data_database: str = "reservation_analytics"

    sqlite_path: Path = ROOT / "local_data" / "reservation_analytics.db"

    use_llm: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"
    default_year: int = 2026

    athena_workgroup: str = "primary"
    athena_output_location: str = "s3://change-me/athena-results/"

    sql_gateway_endpoint: str | None = None
    sql_gateway_user_id: str | None = None
    sql_gateway_token: str | None = None

    @property
    def aws_region(self) -> str:
        return self.data_region

    @property
    def athena_database(self) -> str:
        return self.data_database


def load_settings(env_file: str = "config/local.env") -> Settings:
    values = _read_env(ROOT / env_file)
    values.update(_read_env(ROOT / ".env"))

    return Settings(
        app_env=_value(values, "APP_ENV", "local"),
        backend=_value(values, "DATA_BACKEND", "sqlite").lower(),
        knowledge_dir=ROOT / _value(values, "KNOWLEDGE_DIR", "knowledge"),
        data_region=_value(values, "DATA_REGION", "local"),
        data_cluster=_value(values, "DATA_CLUSTER", "local"),
        data_database=_value(values, "DATA_DATABASE", "reservation_analytics"),
        sqlite_path=ROOT / _value(values, "SQLITE_PATH", "local_data/reservation_analytics.db"),
        use_llm=_value(values, "LLM_ENABLED", "false").lower() == "true",
        openai_api_key=_value(values, "OPENAI_API_KEY") or None,
        openai_model=_value(values, "OPENAI_MODEL", "gpt-4.1-mini"),
        embedding_model=_value(values, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        default_year=int(_value(values, "DEFAULT_CAMPAIGN_YEAR", "2026")),
        athena_workgroup=_value(values, "ATHENA_WORKGROUP", "primary"),
        athena_output_location=_value(
            values,
            "ATHENA_OUTPUT_LOCATION",
            "s3://change-me/athena-results/",
        ),
        sql_gateway_endpoint=_value(values, "SQL_GATEWAY_ENDPOINT") or None,
        sql_gateway_user_id=_value(values, "SQL_GATEWAY_USER_ID") or None,
        sql_gateway_token=_value(values, "SQL_GATEWAY_TOKEN") or None,
    )
