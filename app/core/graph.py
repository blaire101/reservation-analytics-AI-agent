from __future__ import annotations

from app.analytics.resolver import CampaignResolver
from app.analytics.service import AnalyticsService
from app.core.extractor import RequestExtractor
from app.core.models import AgentState, Campaign, EntityCandidate, ReservationQuery, ResolutionResult
from app.core.session import InMemorySessionStore
from app.core.validation import missing_analytics_context
from app.data.backend import QueryBackend
from app.knowledge.rag import KnowledgeRAG
from app.settings import Settings


class ReservationAgent:
    """Route questions, resolve business context, and resume clarification by session."""

    def __init__(self, settings: Settings, backend: QueryBackend):
        self.extractor = RequestExtractor(settings)
        self.knowledge = KnowledgeRAG(settings)
        self.resolver = CampaignResolver(backend, settings)
        self.analytics = AnalyticsService(backend)
        self.sessions = InMemorySessionStore()
        self.graph = self._build_graph()

    # ----- LangGraph nodes -----

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
        campaign = Campaign(**state["resolved_context"])
        answer = self.analytics.run(
            metric=state["metric"],
            campaign=campaign,
            detail_requested=state.get("detail_requested", False),
        )
        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": answer,
        }

    # ----- Public entry point -----

    def invoke(self, question: str, session_id: str = "demo-session") -> AgentState:
        previous = self.sessions.get(session_id)

        if self._is_waiting_for_clarification(previous):
            result = self._resume_clarification(question, previous)
        else:
            result = self._run_new_question(question, session_id)

        self._remember_only_pending_clarification(session_id, result)
        return result


    def _run_new_question(self, question: str, session_id: str) -> AgentState:
        initial: AgentState = {"question": question, "session_id": session_id}
        if self.graph is not None:
            return self.graph.invoke(initial)

        # Lightweight fallback used only when LangGraph is not installed.
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

    # ----- Clarification resume -----

    def _resume_clarification(
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

    @staticmethod
    def _is_waiting_for_clarification(state: AgentState | None) -> bool:
        return bool(
            state
            and state.get("status") == "clarification"
            and state.get("pending_entity")
        )

    def _remember_only_pending_clarification(
        self,
        session_id: str,
        state: AgentState,
    ) -> None:
        if self._is_waiting_for_clarification(state):
            self.sessions.save(session_id, state)
        else:
            self.sessions.clear(session_id)

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

        if result.status == "resolved" and result.campaign:
            return {
                **base,
                "status": "resolved",
                "resolved_context": result.campaign.model_dump(),
            }

        if result.status == "clarification":
            return {
                **base,
                "status": "clarification",
                "answer": result.message,
                "pending_entity": result.pending_entity or "",
                "candidates": [candidate.model_dump() for candidate in result.candidates],
            }

        return {**base, "status": "not_found", "answer": result.message}

    # ----- Graph definition -----

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
            lambda state: state["intent"],
            {"knowledge": "knowledge", "analytics": "validate"},
        )
        graph.add_edge("knowledge", END)
        graph.add_conditional_edges(
            "validate",
            lambda state: "resolve" if state["status"] == "validated" else "end",
            {"resolve": "resolve", "end": END},
        )
        graph.add_conditional_edges(
            "resolve",
            lambda state: "analytics" if state["status"] == "resolved" else "end",
            {"analytics": "analytics", "end": END},
        )
        graph.add_edge("analytics", END)
        return graph.compile()
