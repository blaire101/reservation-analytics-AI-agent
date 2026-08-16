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
from app.data.backend import QueryBackend
from app.knowledge.rag import KnowledgeRAG
from app.settings import Settings


class ReservationAgent:
    """
    Main orchestration layer.

    Analytics:
        Extract → Validate → Resolve → Analytics

    Knowledge:
        Extract → Knowledge RAG

    Multi-turn:
        Resolve → Clarify → session memory → user reply → confirm()
    """

    def __init__(self, settings: Settings, backend: QueryBackend):
        settings.require_llm()

        self.extractor = RequestExtractor(settings)
        self.knowledge = KnowledgeRAG(settings)
        self.resolver = CampaignResolver(backend, settings)
        self.analytics = AnalyticsService(backend)
        self.sessions = InMemorySessionStore()
        self.graph = self._build_graph()

    def invoke(
        self,
        question: str,
        session_id: str = "demo-session",
    ) -> AgentState:
        """Run a new question or resume a pending clarification."""

        previous = self.sessions.get(session_id)

        if self._waiting(previous):
            result = self._resume(question, previous)
        else:
            result = self.graph.invoke(
                {
                    "question": question,
                    "session_id": session_id,
                }
            )

        if self._waiting(result):
            self.sessions.save(session_id, result)
        else:
            self.sessions.clear(session_id)

        return result

    # -------------------- LangGraph nodes --------------------

    def extract_node(self, state: AgentState) -> AgentState:
        """LLM: question → typed request."""

        request = self.extractor.extract(state["question"])
        return {
            **state,
            "intent": request.intent,
            "metric": request.metric,
            "detail_requested": request.detail_requested,
            "query": request.query.model_dump(),
        }

    def knowledge_node(self, state: AgentState) -> AgentState:
        """Knowledge question → RAG."""

        return {
            **state,
            "route": "knowledge",
            "status": "answered",
            "answer": self.knowledge.answer(state["question"]),
        }

    def validate_node(self, state: AgentState) -> AgentState:
        """Analytics needs at least one business clue."""

        query = ReservationQuery(**state["query"])
        if query.has_business_context():
            return {**state, "status": "validated"}

        return {
            **state,
            "route": "analytics",
            "status": "clarification",
            "answer": "Please provide campaign or other business context.",
        }

    def resolve_node(self, state: AgentState) -> AgentState:
        """User wording → governed IDs."""

        query = ReservationQuery(**state["query"])
        return self._apply_resolution(
            state,
            self.resolver.resolve(query),
        )

    def analytics_node(self, state: AgentState) -> AgentState:
        """Stable context → controlled SQL."""

        context = CampaignContext(**state["resolved_context"])
        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": self.analytics.run(
                metric=state["metric"],
                context=context,
                detail_requested=state.get("detail_requested", False),
            ),
        }

    # -------------------- Multi-turn --------------------

    def _resume(
        self,
        user_answer: str,
        previous: AgentState,
    ) -> AgentState:
        """Use the saved candidates instead of restarting the request."""

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

        return (
            self.analytics_node(state)
            if state["status"] == "resolved"
            else state
        )

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
        """ResolutionResult → AgentState."""

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
                "candidates": [
                    item.model_dump()
                    for item in result.candidates
                ],
            }

        return {**base, "answer": result.message}

    # -------------------- Workflow --------------------

    def _build_graph(self):
        """
        Build the LangGraph workflow.

                        ┌→ knowledge → END
        START → extract
                        └→ validate → resolve → analytics → END

        Validate/resolve may stop early for clarification.
        """

        from langgraph.graph import END, START, StateGraph

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
