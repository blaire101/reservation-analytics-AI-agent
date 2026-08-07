from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # AI runtime is independent from the data backend.
    # mock_mode=True keeps extraction / knowledge retrieval deterministic so the
    # project can run with no external LLM key. LangGraph still runs if installed.
    mock_mode: bool = True

    # Data backend: sqlite (default/local), athena, internal_sql_gateway
    data_backend: str = "sqlite"
    data_region: str = "default"
    data_cluster: str = "local"

    # Local SQL backend. The database is seeded from mock_data/*.csv on startup.
    local_sqlite_path: str = "local_data/reservation_analytics.db"
    local_seed_on_start: bool = True

    # Internal SQL gateway configuration (enterprise lakehouse / Hive / Iceberg).
    sql_gateway_endpoint: str | None = None
    sql_gateway_user_id: str | None = None
    sql_gateway_token: str | None = None
    sql_gateway_catalog: str | None = "iceberg"
    sql_gateway_timeout_seconds: int = 60

    # AWS / Athena backend.
    aws_region: str = "ap-southeast-1"
    dm_database: str = "reservation_dm"
    dm_table: str = "dm_reservation_conversion"
    dim_database: str = "reservation_dim"
    campaign_table: str = "dim_campaign"

    campaign_id_column: str = "campaign_id"
    campaign_name_column: str = "campaign_name"
    campaign_country_column: str = "country"
    campaign_site_column: str = "site"
    campaign_product_id_column: str = "product_id"
    campaign_product_name_column: str = "product_name"
    campaign_start_column: str = "campaign_start_date"
    campaign_end_column: str = "campaign_end_date"

    athena_workgroup: str = "primary"
    athena_output: str = "s3://CHANGE-ME/athena-results/"
    athena_poll_seconds: float = 1.0
    athena_timeout_seconds: int = 60

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    knowledge_path: str = "knowledge/reservation_analytics.md"
    default_campaign_year: int = 2026

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def knowledge_file(self) -> Path:
        p = Path(self.knowledge_path)
        return p if p.is_absolute() else self.project_root / p

    @property
    def mock_campaign_file(self) -> Path:
        return self.project_root / "mock_data" / "dim_campaign.csv"

    @property
    def mock_dm_file(self) -> Path:
        return self.project_root / "mock_data" / "dm_reservation_conversion.csv"

    @property
    def sqlite_file(self) -> Path:
        p = Path(self.local_sqlite_path)
        return p if p.is_absolute() else self.project_root / p
