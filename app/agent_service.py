from __future__ import annotations

from app.config import AppSettings
from app.graph import ReservationAgentGraph
from app.schemas import ChatResponse, ReservationQuery
from app.services.analytics import AnalyticsService
from app.services.backend_factory import build_query_backend
from app.services.campaign_resolver import CampaignResolver
from app.services.extractor import RequestExtractor
from app.services.knowledge import KnowledgeService
from app.services.session_store import SessionStore


class ReservationAgentService:
    def __init__(self, settings: AppSettings | None = None):
        self.settings = settings or AppSettings()
        self.backend = build_query_backend(self.settings)

        self.extractor = RequestExtractor(self.settings)
        self.knowledge = KnowledgeService(self.settings)
        self.resolver = CampaignResolver(self.settings, self.backend)
        self.analytics = AnalyticsService(self.settings, self.backend)
        self.sessions = SessionStore()

        self.graph = ReservationAgentGraph(
            self.settings,
            self.extractor,
            self.knowledge,
            self.resolver,
            self.analytics,
        )

    def chat(self, message: str, session_id: str = "default") -> ChatResponse:
        pending = self.sessions.get(session_id)

        state = self.graph.invoke(
            message,
            prior_query=pending.query if pending else None,
            prior_metric=pending.metric if pending else None,
        )

        query = ReservationQuery(**state["query"]) if state.get("query") else None

        if state.get("status") == "clarification" and query is not None:
            self.sessions.put(session_id, query, state.get("metric", "campaign_summary"))
        else:
            self.sessions.clear(session_id)

        return ChatResponse(
            answer=state.get("answer", "No answer produced."),
            route=state.get("route", "unknown"),
            status=state.get("status", "error"),
            extracted=query,
            resolved_campaign=state.get("resolved_campaign"),
            metric=state.get("metric"),
            debug={
                **state.get("debug", {}),
                "data_backend": self.backend.name,
                "data_region": self.settings.data_region,
                "data_cluster": self.settings.data_cluster,
            },
        )

    def reset(self, session_id: str) -> None:
        self.sessions.clear(session_id)
