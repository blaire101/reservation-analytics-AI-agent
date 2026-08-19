"""Query-backend abstraction and factory.

Analytics code calls the same small ``execute(sql)`` interface whether data is
local SQLite, AWS Athena, or an internal SQL Gateway.
"""

from __future__ import annotations

from typing import Any, Protocol

from app.settings import Settings


class QueryBackend(Protocol):
    """Minimal interface required by entity resolution and analytics services."""

    name: str

    def execute(self, sql: str) -> list[dict[str, Any]]:
        """Execute application-controlled SQL and return rows as dictionaries."""
        ...


def create_backend(settings: Settings) -> QueryBackend:
    """Create the configured backend adapter.

    Args:
        settings: Application settings containing ``DATA_BACKEND``.

    Returns:
        ``SQLiteBackend``, ``AthenaBackend``, or ``SQLGatewayBackend``.

    Design benefit:
        The business logic in resolvers and ``AnalyticsService`` does not care
        where the data physically runs. Only this factory chooses the adapter.
    """
    if settings.backend == 'sqlite':
        from app.analytics.query.sqlite_backend import SQLiteBackend
        return SQLiteBackend(settings)

    if settings.backend == 'athena':
        from app.analytics.query.remote_backend import AthenaBackend
        return AthenaBackend(settings)

    if settings.backend == 'sql_gateway':
        from app.analytics.query.remote_backend import SQLGatewayBackend
        return SQLGatewayBackend(settings)

    raise ValueError(f'Unsupported DATA_BACKEND: {settings.backend}')
