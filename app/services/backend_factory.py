from __future__ import annotations

from app.config import AppSettings
from app.services.athena import AthenaClient
from app.services.sqlite_backend import SQLiteBackend
from app.services.sql_gateway import InternalSQLGatewayClient


def build_query_backend(settings: AppSettings):
    kind = settings.data_backend.strip().lower()
    if kind == "sqlite":
        return SQLiteBackend(settings)
    if kind == "athena":
        return AthenaClient(settings)
    if kind in {"internal_sql_gateway", "sql_gateway"}:
        return InternalSQLGatewayClient(settings)
    raise ValueError(
        f"Unsupported DATA_BACKEND={settings.data_backend!r}. "
        "Use sqlite, athena, or internal_sql_gateway."
    )
