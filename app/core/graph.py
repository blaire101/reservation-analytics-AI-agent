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
    """
    Main application workflow for the Reservation Analytics AI Agent.

    High-level flow:

        User Question
             ↓
        RequestExtractor
             ↓
        ┌─────────────────────────────┐
        │                             │
        │ Knowledge question          │ Analytics question
        │                             │
        ▼                             ▼
    Knowledge RAG                 Validation
        │                             │
        ▼                             ▼
      Answer                     Entity Resolution
                                      │
                                      ▼
                                AnalyticsService
                                      │
                                      ▼
                                    Answer

    The class mainly coordinates other modules.

    Responsibilities:
        - RequestExtractor:
            Understand the user's question and create a typed request.

        - KnowledgeRAG:
            Answer business-definition / metadata questions.

        - CampaignResolver:
            Convert natural-language business entities into governed IDs.

        - AnalyticsService:
            Execute controlled Data Mart queries.

        - InMemorySessionStore:
            Keep clarification candidates between user messages.

        - LangGraph:
            Control the workflow between these steps.

    Important design principle:

        The LLM interprets language.

        Application code controls:
            - validation
            - entity resolution
            - stable IDs
            - SQL execution
    """

    def __init__(
        self,
        settings: Settings,
        backend: QueryBackend,
    ):
        """
        Create all application components.

        Dependency flow:

            Settings
               │
               ├── RequestExtractor
               ├── KnowledgeRAG
               └── CampaignResolver

            QueryBackend
               │
               ├── CampaignResolver
               └── AnalyticsService

        The LangGraph workflow is built once when the Agent starts.
        """

        # Natural language → typed request.
        self.extractor = RequestExtractor(settings)

        # Knowledge-question RAG path.
        self.knowledge = KnowledgeRAG(settings)

        # Natural-language entities → governed business context.
        self.resolver = CampaignResolver(
            backend,
            settings,
        )

        # Controlled Data Mart queries.
        self.analytics = AnalyticsService(backend)

        # Lightweight clarification memory:
        #
        # session_id
        #     ↓
        # pending entity + candidates + current query
        #
        # This is intentionally in-process for the prototype.
        self.sessions = InMemorySessionStore()

        # Build the LangGraph workflow.
        self.graph = self._build_graph()

    # ==============================================================
    # Public API
    # ==============================================================

    def invoke(
        self,
        question: str,
        session_id: str = "demo-session",
    ) -> AgentState:
        """
        Main entry point for one user message.

        Example:

            agent.invoke(
                question="How many users reserved for CMP001 in Germany?",
                session_id="user-123-chat-456",
            )

        There are two possible situations.

        Case 1 — New question:

            User message
                ↓
            no pending clarification
                ↓
            _run()
                ↓
            normal LangGraph workflow

        Case 2 — Clarification reply:

            Previous question
                ↓
            Agent asked user to choose a candidate
                ↓
            candidate state saved under session_id
                ↓
            next user message
                ↓
            _resume()
                ↓
            continue entity resolution

        Session lifecycle:

            clarification required
                → save session

            final answer / not found
                → clear session
        """

        # Check whether this session is waiting for a clarification reply.
        previous = self.sessions.get(session_id)

        if self._waiting(previous):
            # Example:
            #
            # Agent:
            #   "Please choose campaign:
            #    1. CMP001
            #    2. CMP002"
            #
            # User:
            #   "1"
            #
            # This path resumes the previous resolution.
            result = self._resume(
                question,
                previous,
            )

        else:
            # Normal new question.
            result = self._run(
                question,
                session_id,
            )

        # Keep state only when another clarification is required.
        if self._waiting(result):
            self.sessions.save(
                session_id,
                result,
            )

        else:
            # Final answer or failure:
            # no pending clarification is needed anymore.
            self.sessions.clear(session_id)

        return result

    # ==============================================================
    # LangGraph Nodes
    #
    # Every node follows the same pattern:
    #
    #     AgentState
    #         ↓
    #     node logic
    #         ↓
    #     updated AgentState
    #
    # AgentState acts like the shared "working memory" of the workflow.
    # ==============================================================

    def extract_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Node 1: Understand the user's question.

        Input state:
            {
                "question": "...",
                "session_id": "..."
            }

        RequestExtractor returns a typed request such as:
            intent = "analytics"
            metric = "reserved_users"
            query = {
                "country": "Germany",
                "campaign_id": "CMP001",
                "product": None
            }
        Output state then contains:
            question
            session_id
            intent
            metric
            detail_requested
            query
        Important:
            The extractor understands user wording.
            It should NOT invent warehouse IDs that the user did not provide.
            Entity grounding happens later in CampaignResolver.
        """

        request = self.extractor.extract(
            state["question"]
        )

        return {
            **state,
            # Determines which LangGraph branch to use.
            "intent": request.intent,
            "metric": request.metric, # Example: reserved_users, ordered_users, conversion_rate
            # True when the user asks for user-level details.
            "detail_requested": request.detail_requested,
            # Convert the Pydantic model to a plain dictionary
            # because AgentState stores serializable workflow state.
            "query": request.query.model_dump(),
        }

    def knowledge_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Knowledge-question path.
        Example questions:
            "What does reserved_not_ordered mean?"
            "What is the grain of the Data Mart?"
            "How is conversion rate defined?"
        Flow:
            question
                ↓
            KnowledgeRAG
                ↓
            LlamaIndex / FAISS retrieval
                ↓
            grounded answer
        This path explains business knowledge.
        """

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
        """
        Validate whether enough analytics context exists.

        Example:
            User:
                "How many users reserved?"
        This may be too broad because the system still needs
        enough campaign context to identify the intended scope.

        Flow:
            state["query"]
                ↓
            ReservationQuery
                ↓
            missing_analytics_context()
                ↓
            no missing fields
                → status = validated
            missing fields
                → status = clarification
                → ask the user

        Important:
            Validation does NOT resolve entity names.
            It only checks whether the request contains enough
            information to continue into entity resolution.
        """

        query = ReservationQuery(
            **state["query"]
        )

        missing = missing_analytics_context(
            query
        )

        if not missing:
            return {
                **state,
                "status": "validated",
            }

        return {
            **state,
            "route": "analytics",
            "status": "clarification",
            "answer": (
                "Please provide "
                + ", ".join(missing)
                + ". I will not guess."
            ),
        }

    def resolve_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Resolve natural-language business context into governed IDs.
        Example input:

            {
                "country": "Germany",
                "campaign_name": "Mi 17 launch",
                "product": None
            }

        Resolver flow:
            country if supplied
                ↓
            product if supplied
                ↓
            campaign
                ↓
            stable CampaignContext

        Example:
            Germany + CMP001
            → campaign-level analytics
            → all products inside CMP001

        But:
            Germany + CMP001 + Mi 17 Pro
            → product-level analytics
            → only that product

        If several governed candidates are possible:
            resolver
                ↓
            ResolutionResult(status="clarification")
                ↓
            candidates saved in session memory
                ↓
            user confirms on next message
        """

        query = ReservationQuery(
            **state["query"]
        )

        result = self.resolver.resolve(
            query
        )

        # Convert the resolver's typed result
        # into AgentState fields used by LangGraph.
        return self._apply_resolution(
            state,
            result,
        )

    def analytics_node(
        self,
        state: AgentState,
    ) -> AgentState:
        """
        Run controlled analytics against the trusted Data Mart.

        Input example:

            resolved_context = {
                "campaign_id": "CMP001",
                "campaign_name": "Mi 17 Launch",
                "country_code": "DE",
                "country_name": "Germany",
                "product_id": None,
                "product_name": None
            }

        If product_id is None:

            SQL filters by:
                campaign_id
                country_code

            → aggregate ALL products in the campaign.

        If product_id exists:

            SQL filters by:
                campaign_id
                country_code
                product_id

            → product-level analytics.

        AnalyticsService contains the allowlisted SQL logic.
        The LLM does not generate unrestricted analytics SQL here.
        """

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

    # ==============================================================
    # Run / Resume
    # ==============================================================

    def _run(
        self,
        question: str,
        session_id: str,
    ) -> AgentState:
        """
        Start a normal new request.

        Initial AgentState:

            {
                "question": "...",
                "session_id": "..."
            }

        Normal LangGraph flow:

                             ┌→ knowledge → END
                             │
            START → extract ─┤
                             │
                             └→ validate
                                   ↓
                                resolve
                                   ↓
                               analytics
                                   ↓
                                  END

        Validation or resolution can stop early
        when clarification is required.
        """

        initial: AgentState = {
            "question": question,
            "session_id": session_id,
        }

        # Normal production path:
        # execute the compiled LangGraph workflow.
        if self.graph is not None:
            return self.graph.invoke(
                initial
            )

        # ----------------------------------------------------------
        # Fallback path
        # ----------------------------------------------------------
        #
        # This keeps the project runnable even when LangGraph
        # is not installed.
        #
        # It manually executes the same logical workflow.
        # ----------------------------------------------------------

        state = self.extract_node(
            initial
        )

        # Knowledge questions bypass analytics.
        if state["intent"] == "knowledge":
            return self.knowledge_node(
                state
            )

        # Analytics path:
        #
        # validate
        #     ↓
        # resolve
        #     ↓
        # analytics

        state = self.validate_node(
            state
        )
        # Stop when validation asks for more information.
        if state["status"] != "validated":
            return state

        state = self.resolve_node(
            state
        )
        # Stop when resolution requires clarification
        # or no governed candidate was found.
        if state["status"] != "resolved":
            return state

        # Stable business context is ready.
        return self.analytics_node(
            state
        )

    def _resume(
        self,
        user_answer: str,
        previous: AgentState,
    ) -> AgentState:
        """
        Resume a previous entity-resolution clarification.

        Example conversation:

            User:
                "How many reserved users for the Germany launch?"

            Agent:
                "Please choose campaign:
                 1. CMP001
                 2. CMP002"

            Session memory stores:

                pending_entity = "campaign"

                candidates = [
                    CMP001,
                    CMP002
                ]

                query = previous structured query

            User:
                "1"

        Then:

            _resume()
                ↓
            resolver.confirm(...)
                ↓
            choose CMP001
                ↓
            continue resolver.resolve(...)
                ↓
            stable context
                ↓
            analytics_node()

        The user does not need to repeat the original question.
        """

        # Ask the resolver to interpret the clarification answer
        # only against the candidates from the previous turn.
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

        # Merge the new resolution result back into AgentState.
        state = self._apply_resolution(
            {
                **previous,

                # Replace the current message with the clarification reply.
                "question": user_answer,
            },
            result,
        )

        # If the clarification completed entity resolution,
        # immediately continue to analytics.
        if state["status"] == "resolved":
            return self.analytics_node(
                state
            )

        # Otherwise another clarification may still be required.
        return state

    # ==============================================================
    # State Helpers
    # ==============================================================

    @staticmethod
    def _waiting(
        state: AgentState | None,
    ) -> bool:
        """
        Return True when the Agent is waiting for a clarification reply.

        We require BOTH:

            status == "clarification"

        and:

            pending_entity exists

        Example:

            {
                "status": "clarification",
                "pending_entity": "campaign"
            }

        This tells invoke():

            save this state under session_id
            and resume it on the next user message.
        """

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
        """
        Convert ResolutionResult into LangGraph AgentState.

        CampaignResolver works with typed Pydantic models:

            ResolutionResult

        LangGraph works with:

            AgentState

        This method is the adapter between them.

        There are three possible resolver outcomes:

            1. resolved
            2. clarification
            3. not_found
        """

        # Fields shared by every resolver outcome.
        base: AgentState = {
            **state,

            # The resolver may have added stable IDs
            # such as country_code or campaign_id.
            "query": result.query.model_dump(),

            "route": "analytics",
            "status": result.status,
        }

        # ----------------------------------------------------------
        # Case 1: resolved
        # ----------------------------------------------------------
        #
        # Stable business context is ready for AnalyticsService.
        #
        # Example:
        #
        # CampaignContext(
        #     campaign_id="CMP001",
        #     country_code="DE",
        #     product_id=None,
        # )
        #
        if (
            result.status == "resolved"
            and result.context
        ):
            return {
                **base,
                "resolved_context": (
                    result.context.model_dump()
                ),
            }

        # ----------------------------------------------------------
        # Case 2: clarification
        # ----------------------------------------------------------
        #
        # Keep:
        #
        #   pending_entity
        #   candidates
        #   current query
        #
        # so the next user message can resume this request.
        #
        if result.status == "clarification":
            return {
                **base,
                "answer": result.message,

                "pending_entity": (
                    result.pending_entity or ""
                ),

                "candidates": [
                    candidate.model_dump()
                    for candidate in result.candidates
                ],
            }

        # ----------------------------------------------------------
        # Case 3: not_found
        # ----------------------------------------------------------
        return {
            **base,
            "answer": result.message,
        }

    # ==============================================================
    # LangGraph Definition
    # ==============================================================

    def _build_graph(self):
        """
        Build and compile the LangGraph workflow.

        AgentState is the shared state passed between all nodes.

        Each node:

            reads AgentState
                ↓
            performs one responsibility
                ↓
            updates AgentState
                ↓
            passes it to the next node

        ------------------------------------------------------------
        Complete workflow
        ------------------------------------------------------------

                           ┌──────────────────────┐
                           │                      ▼
        START → extract ───┤               knowledge
                           │                      │
                           │                      ▼
                           │                     END
                           │
                           ▼
                        validate
                           │
                    valid? │
                     yes   │
                           ▼
                        resolve
                           │
                  resolved?│
                     yes   │
                           ▼
                       analytics
                           │
                           ▼
                          END

        Early-stop situations:

            validate
                → missing context
                → clarification
                → END

            resolve
                → ambiguous candidate
                → clarification
                → END

            resolve
                → no candidate
                → not_found
                → END

        Clarification is resumed outside the graph by:

            invoke()
                ↓
            session store
                ↓
            _resume()
        """

        try:
            from langgraph.graph import (
                END,
                START,
                StateGraph,
            )

        except ImportError:
            # _run() contains a small manual fallback
            # with the same logical workflow.
            return None

        # ----------------------------------------------------------
        # Step 1: Create the graph
        # ----------------------------------------------------------
        #
        # AgentState defines the shared state structure
        # passed between every workflow node.
        #
        graph = StateGraph(
            AgentState
        )

        # ----------------------------------------------------------
        # Step 2: Register workflow nodes
        # ----------------------------------------------------------
        #
        # Syntax:
        #
        #     graph.add_node(
        #         "node_name",
        #         python_function
        #     )
        #
        # For example:
        #
        #     "extract"
        #         ↓
        #     self.extract_node
        #
        # means LangGraph executes self.extract_node
        # whenever the workflow enters the "extract" node.
        #

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

        # ----------------------------------------------------------
        # Step 3: Define edges
        # ----------------------------------------------------------

        # Every request starts with extraction.
        #
        # START
        #   ↓
        # extract
        #
        graph.add_edge(
            START,
            "extract",
        )

        # ----------------------------------------------------------
        # Route by intent
        # ----------------------------------------------------------
        #
        # After extract_node:
        #
        # state["intent"] == "knowledge"
        #     → knowledge
        #
        # state["intent"] == "analytics"
        #     → validate
        #
        graph.add_conditional_edges(
            "extract",

            # Routing function:
            # read the intent from AgentState.
            lambda state: state["intent"],

            # Routing table.
            {
                "knowledge": "knowledge",
                "analytics": "validate",
            },
        )

        # Knowledge questions finish after the RAG answer.
        #
        # knowledge
        #     ↓
        #    END
        #
        graph.add_edge(
            "knowledge",
            END,
        )

        # ----------------------------------------------------------
        # Validation routing
        # ----------------------------------------------------------
        #
        # status == "validated"
        #     → continue to resolve
        #
        # otherwise
        #     → END
        #
        # "otherwise" usually means:
        #
        #     clarification required
        #
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

        # ----------------------------------------------------------
        # Resolution routing
        # ----------------------------------------------------------
        #
        # status == "resolved"
        #     → analytics
        #
        # clarification / not_found
        #     → END
        #
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

        # Analytics always finishes the request.
        #
        # analytics
        #     ↓
        #    END
        #
        graph.add_edge(
            "analytics",
            END,
        )

        # ----------------------------------------------------------
        # Step 4: Compile
        # ----------------------------------------------------------
        #
        # Before compile():
        #     graph is the workflow definition.
        #
        # After compile():
        #     graph becomes executable:
        #
        #         self.graph.invoke(initial_state)
        #
        return graph.compile()