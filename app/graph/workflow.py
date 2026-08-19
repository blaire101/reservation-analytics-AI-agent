"""Build the complete LangGraph workflow for the Reservation Analytics Agent.

Core flow:
    User Question
        -> Extract Structured Business Plan
        -> Route by intent
            -> Knowledge: RAG -> Answer
            -> Analytics: Validate -> Resolve -> Controlled SQL -> Answer
"""

from __future__ import annotations

from app.analytics.resolution.service import BusinessResolver
from app.analytics.service import AnalyticsService
from app.graph.state import AgentState
from app.graph.nodes.extract import RequestExtractor
from app.graph.nodes import analytics, extract, knowledge, resolve, validate
from app.rag.service import KnowledgeRAG


class ReservationAgent:
    """Coordinate the two controlled answer paths through LangGraph."""

    def __init__(self, settings, backend):
        """Create the services used by the graph and compile the workflow.

        Args:
            settings: Application/LLM configuration.
            backend: Query backend used by entity resolution and analytics.
        """
        # LLM -> typed business plan.
        self.extractor = RequestExtractor(settings)

        # Knowledge path -> LlamaIndex + FAISS RAG.
        self.rag = KnowledgeRAG(settings)

        # Analytics path -> governed entity resolution.
        self.resolver = BusinessResolver(backend)

        # Analytics path -> allowlisted controlled SQL.
        self.analytics = AnalyticsService(backend)

        # Compile once and reuse for every question.
        self.graph = self._build_graph()

    def invoke(self, question: str) -> AgentState:
        """Run one user question through the compiled LangGraph workflow.

        Args:
            question: Raw natural-language business question.

        Returns:
            Final ``AgentState`` containing answer, route, and status.
        """
        return self.graph.invoke({'question': question})

    def _build_graph(self):
        """Define nodes, edges, and routing rules, then compile the graph.

        Routing logic:
            1. Every question starts at ``extract``.
            2. ``knowledge`` intent goes directly to RAG.
            3. ``analytics`` intent goes to validation.
            4. Valid analytics context proceeds to entity resolution.
            5. Resolved context proceeds to controlled analytics.
            6. Clarification/not-found states end early.

        Returns:
            A compiled LangGraph runnable.
        """
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(AgentState)

        # ----- Define nodes -----
        graph.add_node('extract', lambda state: extract.run(self.extractor, state))
        graph.add_node('knowledge', lambda state: knowledge.run(self.rag, state))
        graph.add_node('validate', validate.run)
        graph.add_node('resolve', lambda state: resolve.run(self.resolver, state))
        graph.add_node('analytics', lambda state: analytics.run(self.analytics, state))

        # ----- Start: every request first becomes a structured business plan -----
        graph.add_edge(START, 'extract')

        # ----- Route by LLM-extracted intent -----
        graph.add_conditional_edges(
            'extract',
            lambda state: state['intent'],
            {
                'knowledge': 'knowledge',
                'analytics': 'validate',
            },
        )

        # Knowledge questions finish after RAG answers them.
        graph.add_edge('knowledge', END)

        # Analytics continues only when validation succeeds.
        graph.add_conditional_edges(
            'validate',
            lambda state: 'resolve' if state['status'] == 'validated' else 'end',
            {
                'resolve': 'resolve',
                'end': END,
            },
        )

        # Analytics SQL runs only after entity resolution returns stable IDs.
        graph.add_conditional_edges(
            'resolve',
            lambda state: 'analytics' if state['status'] == 'resolved' else 'end',
            {
                'analytics': 'analytics',
                'end': END,
            },
        )

        graph.add_edge('analytics', END)

        return graph.compile()
