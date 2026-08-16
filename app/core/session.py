from __future__ import annotations

from app.core.models import AgentState


class InMemorySessionStore:
    """Small prototype store for pending clarification state."""

    def __init__(self) -> None:
        self._items: dict[str, AgentState] = {}

    def get(self, session_id: str) -> AgentState | None:
        return self._items.get(session_id)

    def save(self, session_id: str, state: AgentState) -> None:
        self._items[session_id] = state

    def clear(self, session_id: str) -> None:
        self._items.pop(session_id, None)
