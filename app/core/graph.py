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
    Main Agent workflow.

    New request:

        User Question
             ↓
          Extract
             ↓
        ┌────┴─────┐
        │          │
    Knowledge   Analytics
        │          │
       RAG      Validate
                   ↓
                Resolve
                   ↓
               Analytics

    Multi-turn clarification:

        Resolve
          ↓
      Ambiguous
          ↓
       Clarify
          ↓
    save by session_id
          ↓
      user replies
          ↓
        resume
    """

    def __init__(
        self,
        settings: Settings,
        backend: QueryBackend,
    ):
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
        """
        Entry point for every user message.

        If this session is waiting for clarification:
            → resume the previous request

        Otherwise:
            → start a new LangGraph workflow
        """

        previous = self.sessions.get(session_id)

        if self._is_waiting(previous):
            result = self._resume(
                user_answer=question,
                previous=previous,
            )
        else:
            result = self.graph.invoke(
                {
                    "question": question,
                    "session_id": session_id,
                }
            )

        # Save state only while waiting for entity clarification.
        if self._is_waiting(result):
            self.sessions.save(session_id, result)
        else:
            self.sessions.clear(session_id)

        return result

    # ==========================================================
    # LangGraph nodes
    # ==========================================================

    def extract_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """LLM: natural language → typed request."""

        request = self.extractor.extract(
            state["question"]
        )

        return {
            **state,
            "intent": request.intent,
            "metric": request.metric,
            "detail_requested": request.detail_requested,
            "query": request.query.model_dump(),
        }

    def knowledge_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Knowledge question → RAG answer."""

        answer = self.knowledge.answer(
            state["question"]
        )

        return {
            **state,
            "route": "knowledge",
            "status": "answered",
            "answer": answer,
        }

    def validate_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Check that analytics has at least one business clue."""

        query = ReservationQuery(
            **state["query"]
        )

        if query.has_business_context():
            return {
                **state,
                "status": "validated",
            }

        return {
            **state,
            "route": "analytics",
            "status": "clarification",
            "answer": (
                "Please provide campaign "
                "or other business context."
            ),
        }

    def resolve_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Natural-language entities → governed IDs."""

        query = ReservationQuery(
            **state["query"]
        )

        result = self.resolver.resolve(query)

        return self._resolution_to_state(
            state,
            result,
        )

    def analytics_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """Stable context → controlled Data Mart SQL."""

        context = CampaignContext(
            **state["resolved_context"]
        )

        answer = self.analytics.run(
            metric=state["metric"],
            context=context,
            detail_requested=state.get(
                "detail_requested",
                False,
            ),
        )

        return {
            **state,
            "route": "analytics",
            "status": "answered",
            "answer": answer,
        }

    # ==========================================================
    # Multi-turn clarification
    # ==========================================================

    def _resume(
        self,
        user_answer: str,
        previous: AgentState,
    ) -> AgentState:
        """
        Continue a pending entity clarification.

        We reuse:
            - pending entity
            - candidate list
            - structured query
        """

        result = self.resolver.confirm(
            entity_type=previous["pending_entity"],
            user_answer=user_answer,
            candidates=[
                EntityCandidate(**item)
                for item in previous.get(
                    "candidates",
                    [],
                )
            ],
            raw_query=ReservationQuery(
                **previous["query"]
            ),
        )

        state = self._resolution_to_state(
            {
                **previous,
                "question": user_answer,
            },
            result,
        )

        if state["status"] == "resolved":
            return self.analytics_node(state)

        return state

    @staticmethod
    def _is_waiting(
        state: AgentState | None,
    ) -> bool:
        """True when the Agent is waiting for entity clarification."""

        return bool(
            state
            and state.get("status") == "clarification"
            and state.get("pending_entity")
        )

    @staticmethod
    def _resolution_to_state(
        state: AgentState,
        result: ResolutionResult,
    ) -> AgentState:
        """Convert ResolutionResult into AgentState."""

        updated: AgentState = {
            **state,
            "query": result.query.model_dump(),
            "route": "analytics",
            "status": result.status,
        }

        # Resolution completed.
        if (
            result.status == "resolved"
            and result.context
        ):
            return {
                **updated,
                "resolved_context": (
                    result.context.model_dump()
                ),
            }

        # Need one more user message.
        if result.status == "clarification":
            return {
                **updated,
                "answer": result.message,
                "pending_entity": (
                    result.pending_entity or ""
                ),
                "candidates": [
                    candidate.model_dump()
                    for candidate in result.candidates
                ],
            }

        # Not found or other controlled result.
        return {
            **updated,
            "answer": result.message,
        }

    # ==========================================================
    # LangGraph definition
    # ==========================================================

    def _build_graph(self):
        """
        Build five workflow nodes:

            extract
              ├─ knowledge → END
              └─ validate → resolve → analytics → END

        Validate and Resolve can stop early.
        """

        from langgraph.graph import (
            END,
            START,
            StateGraph,
        )

        graph = StateGraph(AgentState)

        # Register nodes.
        graph.add_node(
            "extract",
            self.extract_node,
        )
        graph.add_node(
            "knowledge",
            self.knowledge_node,
        )
        graph.add_node(
            "validate",
            self.validate_node,
        )
        graph.add_node(
            "resolve",
            self.resolve_node,
        )
        graph.add_node(
            "analytics",
            self.analytics_node,
        )

        # START → Extract
        graph.add_edge(
            START,
            "extract",
        )

        # Knowledge or Analytics?
        graph.add_conditional_edges(
            "extract",
            lambda state: state["intent"],
            {
                "knowledge": "knowledge",
                "analytics": "validate",
            },
        )

        graph.add_edge(
            "knowledge",
            END,
        )

        # Validation can stop early.
        graph.add_conditional_edges(
            "validate",
            lambda state: (
                "resolve"
                if state["status"] == "validated"
                else "end"
            ),
            {
                "resolve": "resolve",
                "end": END,
            },
        )

        # Resolution can stop for clarification.
        graph.add_conditional_edges(
            "resolve",
            lambda state: (
                "analytics"
                if state["status"] == "resolved"
                else "end"
            ),
            {
                "analytics": "analytics",
                "end": END,
            },
        )

        graph.add_edge(
            "analytics",
            END,
        )

        return graph.compile()
