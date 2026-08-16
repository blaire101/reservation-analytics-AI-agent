from __future__ import annotations

from app.analytics.resolver import CampaignResolver
from app.analytics.service import AnalyticsService
from app.core.extractor import RequestExtractor
from app.core.models import (
    AgentState,
    CampaignContext,
    EntityCandidate,
    ReservationQuery,
    ResolutionResult,
)
from app.core.session import InMemorySessionStore
from app.core.validation import missing_analytics_context
from app.data.backend import QueryBackend
from app.knowledge.rag import KnowledgeRAG
from app.settings import Settings


class ReservationAgent:
    """The application workflow: extract → route → resolve → answer."""

    def __init__(self, settings: Settings, backend: QueryBackend):
        self.extractor = RequestExtractor(settings)
        self.knowledge = KnowledgeRAG(settings)
        self.resolver = CampaignResolver(backend, settings)
        self.analytics = AnalyticsService(backend)
        self.sessions = InMemorySessionStore()
        self.graph = self._build_graph()

    # ---------- Public API ----------

    def invoke(
        self,
        question: str,
        session_id: str = "demo-session",
    ) -> AgentState:
        previous = self.sessions.get(session_id)

        if self._waiting(previous):
            result = self._resume(question, previous)
        else:
            result = self._run(question, session_id)

        if self._waiting(result):
            self.sessions.save(session_id, result)
        else:
            self.sessions.clear(session_id)

        return result

    # ---------- LangGraph nodes ----------

    def extract_node(self, state: AgentState) -> AgentState:
        request = self.extractor.extract(state["question"])
        return {
            **state,
            "intent": request.intent,
            "metric": request.metric,
            "detail_requested": request.detail_requested,
            "query": request.query.model_dump(),
        }

    def knowledge_node(self, state: AgentState) -> AgentState:
        return {
            **state,
            "route": "knowledge",
            "status": "answered",
            "answer": self.knowledge.answer(state["question"]),
        }

    def validate_node(self, state: AgentState) -> AgentState:
        query = ReservationQuery(**state["query"])
        missing = missing_analytics_context(query)
        if not missing:
            return {**state, "status": "validated"}

        return {
            **state,
            "route": "analytics",
            "status": "clarification",
            "answer": "Please provide " + ", ".join(missing) + ". I will not guess.",
        }

    def resolve_node(self, state: AgentState) -> AgentState:
        query = ReservationQuery(**state["query"])
        return self._apply_resolution(state, self.resolver.resolve(query))

    def analytics_node(self, state: AgentState) -> AgentState:
        context = CampaignContext(**state["resolved_context"])
        answer = self.analytics.run(
            metric=state["metric"],
            context=context,
            detail_requested=state.get("detail_requested", False),
        )
        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": answer,
        }

    # ---------- Run / resume ----------

    def _run(self, question: str, session_id: str) -> AgentState:
        initial: AgentState = {
            "question": question,
            "session_id": session_id,
        }

        if self.graph is not None:
            return self.graph.invoke(initial)

        # Small fallback when LangGraph is not installed.
        state = self.extract_node(initial)
        if state["intent"] == "knowledge":
            return self.knowledge_node(state)

        state = self.validate_node(state)
        if state["status"] != "validated":
            return state

        state = self.resolve_node(state)
        if state["status"] != "resolved":
            return state

        return self.analytics_node(state)

    def _resume(
        self,
        user_answer: str,
        previous: AgentState,
    ) -> AgentState:
        result = self.resolver.confirm(
            entity_type=previous["pending_entity"],
            user_answer=user_answer,
            candidates=[
                EntityCandidate(**item)
                for item in previous.get("candidates", [])
            ],
            raw_query=ReservationQuery(**previous["query"]),
        )

        state = self._apply_resolution(
            {**previous, "question": user_answer},
            result,
        )
        if state["status"] == "resolved":
            return self.analytics_node(state)
        return state

    # ---------- State conversion ----------

    @staticmethod
    def _waiting(state: AgentState | None) -> bool:
        return bool(
            state
            and state.get("status") == "clarification"
            and state.get("pending_entity")
        )

    @staticmethod
    def _apply_resolution(
        state: AgentState,
        result: ResolutionResult,
    ) -> AgentState:
        base: AgentState = {
            **state,
            "query": result.query.model_dump(),
            "route": "analytics",
            "status": result.status,
        }

        if result.status == "resolved" and result.context:
            return {
                **base,
                "resolved_context": result.context.model_dump(),
            }

        if result.status == "clarification":
            return {
                **base,
                "answer": result.message,
                "pending_entity": result.pending_entity or "",
                "candidates": [c.model_dump() for c in result.candidates],
            }

        return {**base, "answer": result.message}

    # ---------- Graph definition ----------

    def _build_graph(self):
        try:
            from langgraph.graph import END, START, StateGraph
        except ImportError:
            return None

        graph = StateGraph(AgentState)
        graph.add_node("extract", self.extract_node)
        graph.add_node("knowledge", self.knowledge_node)
        graph.add_node("validate", self.validate_node)
        graph.add_node("resolve", self.resolve_node)
        graph.add_node("analytics", self.analytics_node)

        graph.add_edge(START, "extract")
        graph.add_conditional_edges(
            "extract",
            lambda s: s["intent"],
            {"knowledge": "knowledge", "analytics": "validate"},
        )
        graph.add_edge("knowledge", END)
        graph.add_conditional_edges(
            "validate",
            lambda s: "resolve" if s["status"] == "validated" else "end",
            {"resolve": "resolve", "end": END},
        )
        graph.add_conditional_edges(
            "resolve",
            lambda s: "analytics" if s["status"] == "resolved" else "end",
            {"analytics": "analytics", "end": END},
        )
        graph.add_edge("analytics", END)

        return graph.compile()
