from __future__ import annotations

from dataclasses import dataclass
from app.schemas import ReservationQuery, MetricName


@dataclass
class PendingContext:
    query: ReservationQuery
    metric: MetricName


class SessionStore:
    """
    Prototype-only in-memory clarification state.
    Production could replace this with Redis, DynamoDB, or LangGraph persistence.
    """

    def __init__(self):
        self._pending: dict[str, PendingContext] = {}

    def get(self, session_id: str) -> PendingContext | None:
        return self._pending.get(session_id)

    def put(self, session_id: str, query: ReservationQuery, metric: MetricName) -> None:
        self._pending[session_id] = PendingContext(query=query, metric=metric)

    def clear(self, session_id: str) -> None:
        self._pending.pop(session_id, None)
