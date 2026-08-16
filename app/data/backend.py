from __future__ import annotations

from typing import Any, Protocol

from app.settings import Settings


class QueryBackend(Protocol):
    """Minimal data-access contract used by the application."""

    name: str

    def execute(self, sql: str) -> list[dict[str, Any]]:
        ...


def create_backend(settings: Settings) -> QueryBackend:
    """Create the configured SQL backend without changing analytics code."""

    if settings.backend == "sqlite":
        from app.data.sqlite import SQLiteBackend

        return SQLiteBackend(settings)

    if settings.backend == "athena":
        from app.data.remote import AthenaBackend

        return AthenaBackend(settings)

    if settings.backend == "sql_gateway":
        from app.data.remote import SQLGatewayBackend

        return SQLGatewayBackend(settings)

    raise ValueError(f"Unsupported DATA_BACKEND: {settings.backend}")
