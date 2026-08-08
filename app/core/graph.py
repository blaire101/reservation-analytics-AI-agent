from __future__ import annotations

from app.analytics.resolver import CampaignResolver, missing_context
from app.analytics.service import AnalyticsService
from app.core.extractor import RequestExtractor
from app.core.models import AgentState, Campaign, ReservationQuery
from app.knowledge.rag import KnowledgeRAG
from app.settings import Settings


class ReservationAgent:
    def __init__(self, settings: Settings, backend):
        self.extractor = RequestExtractor(settings)
        self.knowledge = KnowledgeRAG(settings)
        self.resolver = CampaignResolver(backend)
        self.analytics = AnalyticsService(backend)
        self._graph = self._build_langgraph()

    def extract_node(self, state: AgentState) -> AgentState:
        request = self.extractor.extract(state["question"])
        return {
            **state,
            "extracted": request.model_dump(),
            "intent": request.intent,
            "metric": request.metric,
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
        missing = missing_context(query)
        if missing:
            return {
                **state,
                "status": "clarification",
                "route": "analytics",
                "answer": "Please provide " + ", ".join(missing) + ". I will not guess.",
            }
        return {**state, "status": "validated"}

    def resolve_node(self, state: AgentState) -> AgentState:
        campaigns = self.resolver.resolve(ReservationQuery(**state["query"]))
        if not campaigns:
            return {
                **state,
                "status": "not_found",
                "answer": "No campaign matched the supplied business context.",
            }
        if len(campaigns) > 1:
            choices = "; ".join(
                f"{item.campaign_id} — {item.campaign_name}" for item in campaigns
            )
            return {
                **state,
                "status": "clarification",
                "answer": "Multiple campaigns matched. Choose one campaign_id: " + choices,
            }
        return {
            **state,
            "campaign": campaigns[0].model_dump(),
            "status": "resolved",
        }

    def analytics_node(self, state: AgentState) -> AgentState:
        campaign = Campaign(**state["campaign"])
        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": self.analytics.run(state["metric"], campaign),
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
        graph.add_conditional_edges("extract", self._after_extract, {
            "knowledge": "knowledge", "validate": "validate"
        })
        graph.add_edge("knowledge", END)
        graph.add_conditional_edges("validate", self._after_validate, {
            "resolve": "resolve", "end": END
        })
        graph.add_conditional_edges("resolve", self._after_resolve, {
            "analytics": "analytics", "end": END
        })
        graph.add_edge("analytics", END)
        return graph.compile()

    def invoke(self, question: str) -> AgentState:
        state: AgentState = {"question": question}
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
