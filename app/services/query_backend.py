from __future__ import annotations

from typing import Any, Protocol


class QueryBackend(Protocol):
    name: str

    def execute(self, sql: str, database: str) -> list[dict[str, Any]]:
        ...
