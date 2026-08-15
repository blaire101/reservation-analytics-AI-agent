from __future__ import annotations

from app.analytics.resolver import CampaignResolver, missing_context
from app.analytics.service import AnalyticsService
from app.core.extractor import RequestExtractor
from app.core.models import AgentState, Campaign, EntityCandidate, ReservationQuery, ResolutionResult
from app.knowledge.rag import KnowledgeRAG
from app.settings import Settings


class ReservationAgent:
    """Stateful reservation agent with a lightweight per-session clarification loop."""

    def __init__(self, settings: Settings, backend):
        self.extractor = RequestExtractor(settings)
        self.knowledge = KnowledgeRAG(settings)
        self.resolver = CampaignResolver(backend, settings)
        self.analytics = AnalyticsService(backend)
        self._sessions: dict[str, AgentState] = {}
        self._graph = self._build_langgraph()

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
        return {**state, "route": "knowledge", "status": "answered", "answer": self.knowledge.answer(state["question"])}

    def validate_node(self, state: AgentState) -> AgentState:
        query = ReservationQuery(**state["query"])
        missing = missing_context(query)
        if missing:
            return {
                **state,
                "status": "clarification",
                "route": "analytics",
                "answer": "Please provide " + ", ".join(missing) + ". I will not guess.",
            }
        return {**state, "status": "validated"}

    def _apply_resolution(self, state: AgentState, result: ResolutionResult) -> AgentState:
        base = {**state, "query": result.query.model_dump(), "route": "analytics", "status": result.status}
        if result.status == "resolved" and result.campaign:
            return {**base, "resolved_context": result.campaign.model_dump(), "status": "resolved"}
        if result.status == "clarification":
            return {
                **base,
                "status": "clarification",
                "answer": result.message,
                "pending_entity": result.pending_entity or "",
                "candidates": [c.model_dump() for c in result.candidates],
            }
        return {**base, "status": "not_found", "answer": result.message}

    def resolve_node(self, state: AgentState) -> AgentState:
        return self._apply_resolution(state, self.resolver.resolve(ReservationQuery(**state["query"])))

    def analytics_node(self, state: AgentState) -> AgentState:
        campaign = Campaign(**state["resolved_context"])
        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": self.analytics.run(state["metric"], campaign, state.get("detail_requested", False)),
        }

    @staticmethod
    def _after_extract(state: AgentState) -> str:
        return "knowledge" if state["intent"] == "knowledge" else "validate"

    @staticmethod
    def _after_validate(state: AgentState) -> str:
        return "end" if state["status"] == "clarification" else "resolve"

    @staticmethod
    def _after_resolve(state: AgentState) -> str:
        return "analytics" if state["status"] == "resolved" else "end"

    def _build_langgraph(self):
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
        graph.add_conditional_edges("extract", self._after_extract, {"knowledge": "knowledge", "validate": "validate"})
        graph.add_edge("knowledge", END)
        graph.add_conditional_edges("validate", self._after_validate, {"resolve": "resolve", "end": END})
        graph.add_conditional_edges("resolve", self._after_resolve, {"analytics": "analytics", "end": END})
        graph.add_edge("analytics", END)
        return graph.compile()

    def _run_new_question(self, question: str, session_id: str) -> AgentState:
        state: AgentState = {"question": question, "session_id": session_id}
        if self._graph is not None:
            return self._graph.invoke(state)
        state = self.extract_node(state)
        if self._after_extract(state) == "knowledge":
            return self.knowledge_node(state)
        state = self.validate_node(state)
        if self._after_validate(state) == "end":
            return state
        state = self.resolve_node(state)
        if self._after_resolve(state) == "end":
            return state
        return self.analytics_node(state)

    def _resume_clarification(self, answer: str, previous: AgentState) -> AgentState:
        result = self.resolver.confirm(
            previous["pending_entity"],
            answer,
            [EntityCandidate(**item) for item in previous.get("candidates", [])],
            ReservationQuery(**previous["query"]),
        )
        state = self._apply_resolution({**previous, "question": answer}, result)
        if state["status"] == "resolved":
            state = self.analytics_node(state)
        return state

    def invoke(self, question: str, session_id: str = "demo-session") -> AgentState:
        previous = self._sessions.get(session_id)
        if previous and previous.get("status") == "clarification" and previous.get("pending_entity"):
            result = self._resume_clarification(question, previous)
        else:
            result = self._run_new_question(question, session_id)

        if result.get("status") == "clarification" and result.get("pending_entity"):
            self._sessions[session_id] = result
        else:
            self._sessions.pop(session_id, None)
        return result
