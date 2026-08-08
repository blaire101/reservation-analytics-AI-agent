from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    backend: str = "sqlite"
    sqlite_path: Path = ROOT / "local_data" / "reservation_analytics.db"

    use_llm: bool = False
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-small"

    knowledge_file: Path = ROOT / "knowledge" / "reservation_analytics.md"
    default_year: int = 2026

    aws_region: str = "ap-southeast-1"
    athena_database: str = "reservation_dm"
    athena_workgroup: str = "primary"
    athena_output: str = "s3://CHANGE-ME/athena-results/"

    sql_gateway_endpoint: str | None = None
    sql_gateway_user_id: str | None = None
    sql_gateway_token: str | None = None
    region: str = "default"
    cluster: str = "local"


def load_settings(env_file: str | None = None) -> Settings:
    if env_file:
        _load_env_file(ROOT / env_file)
    else:
        _load_env_file(ROOT / ".env")

    return Settings(
        backend=os.getenv("DATA_BACKEND", "sqlite").lower(),
        sqlite_path=ROOT / os.getenv("SQLITE_PATH", "local_data/reservation_analytics.db"),
        use_llm=os.getenv("USE_LLM", "false").lower() == "true",
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        default_year=int(os.getenv("DEFAULT_CAMPAIGN_YEAR", "2026")),
        aws_region=os.getenv("AWS_REGION", "ap-southeast-1"),
        athena_database=os.getenv("ATHENA_DATABASE", "reservation_dm"),
        athena_workgroup=os.getenv("ATHENA_WORKGROUP", "primary"),
        athena_output=os.getenv("ATHENA_OUTPUT", "s3://CHANGE-ME/athena-results/"),
        sql_gateway_endpoint=os.getenv("SQL_GATEWAY_ENDPOINT") or None,
        sql_gateway_user_id=os.getenv("SQL_GATEWAY_USER_ID") or None,
        sql_gateway_token=os.getenv("SQL_GATEWAY_TOKEN") or None,
        region=os.getenv("DATA_REGION", "default"),
        cluster=os.getenv("DATA_CLUSTER", "local"),
    )
