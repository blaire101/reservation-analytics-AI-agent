from __future__ import annotations

from typing import Protocol, Any

from app.settings import Settings


class QueryBackend(Protocol):
    name: str

    def execute(self, sql: str) -> list[dict[str, Any]]:
        ...


def create_backend(settings: Settings) -> QueryBackend:
    if settings.backend == "sqlite":
        from app.data.sqlite import SQLiteBackend

        return SQLiteBackend(settings)

    from app.data.remote import AthenaBackend, SQLGatewayBackend

    if settings.backend == "athena":
        return AthenaBackend(settings)
    if settings.backend == "sql_gateway":
        return SQLGatewayBackend(settings)

    raise ValueError(f"Unsupported DATA_BACKEND: {settings.backend}")
