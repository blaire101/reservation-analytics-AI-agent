from __future__ import annotations

from typing import Any, TypedDict

from app.config import AppSettings
from app.schemas import (
    ExtractedRequest,
    ReservationQuery,
    CampaignOption,
    AnalyticsResult,
)
from app.services.extractor import RequestExtractor
from app.services.knowledge import KnowledgeService
from app.services.campaign_resolver import CampaignResolver
from app.services.analytics import AnalyticsService


class AgentState(TypedDict, total=False):
    question: str
    prior_query: dict | None
    prior_metric: str | None

    extracted: dict
    intent: str
    metric: str
    query: dict

    campaigns: list[dict]
    resolved_campaign: dict | None
    analytics_result: dict | None

    status: str
    answer: str
    route: str
    debug: dict


def merge_query(current: ReservationQuery, prior: ReservationQuery | None) -> ReservationQuery:
    if prior is None:
        return current
    data = prior.model_dump()
    for k, v in current.model_dump().items():
        if v is not None:
            data[k] = v
    return ReservationQuery(**data)


def missing_analytics_context(q: ReservationQuery) -> list[str]:
    # A unique campaign_id is sufficient; country/product can be read from dim_campaign.
    if q.campaign_id:
        return []

    missing = []
    if not (q.country or q.site):
        missing.append("country or site")
    if not q.product:
        missing.append("product")
    has_campaign_hint = any(
        [
            q.campaign_name,
            q.campaign_start_date,
            q.campaign_end_date,
            q.campaign_month,
        ]
    )
    if not has_campaign_hint:
        missing.append("campaign")
    return missing


class ReservationAgentGraph:
    def __init__(
        self,
        settings: AppSettings,
        extractor: RequestExtractor,
        knowledge: KnowledgeService,
        resolver: CampaignResolver,
        analytics: AnalyticsService,
    ):
        self.settings = settings
        self.extractor = extractor
        self.knowledge = knowledge
        self.resolver = resolver
        self.analytics = analytics
        self._graph = self._try_build_langgraph()

    # -----------------------------
    # Nodes
    # -----------------------------
    def extract_node(self, state: AgentState) -> AgentState:
        extracted = self.extractor.extract(state["question"])
        prior_query = (
            ReservationQuery(**state["prior_query"])
            if state.get("prior_query")
            else None
        )
        merged = merge_query(extracted.query, prior_query)

        metric = extracted.metric
        if state.get("prior_metric") and prior_query is not None:
            # Follow-up like "CMP001" should keep the prior analytical metric.
            metric = state["prior_metric"]

        return {
            **state,
            "extracted": extracted.model_dump(),
            "intent": extracted.intent,
            "metric": metric,
            "query": merged.model_dump(),
            "debug": {
                **state.get("debug", {}),
                "extraction": extracted.reasoning_summary,
            },
        }

    def knowledge_node(self, state: AgentState) -> AgentState:
        answer = self.knowledge.answer(state["question"])
        return {
            **state,
            "status": "answered",
            "route": "knowledge -> llamaindex",
            "answer": answer,
        }

    def validate_node(self, state: AgentState) -> AgentState:
        q = ReservationQuery(**state["query"])
        missing = missing_analytics_context(q)

        if state.get("metric") == "user_reservation_check" and not q.user_id:
            missing.append("user_id")

        if missing:
            readable = ", ".join(missing)
            return {
                **state,
                "status": "clarification",
                "route": "analytics -> validation",
                "answer": (
                    f"I still need {readable}. "
                    "Please provide the missing business context; I will not guess."
                ),
                "debug": {
                    **state.get("debug", {}),
                    "missing": missing,
                },
            }

        return {
            **state,
            "status": "validated",
            "route": "analytics -> validation",
        }

    def resolve_campaign_node(self, state: AgentState) -> AgentState:
        q = ReservationQuery(**state["query"])
        campaigns = self.resolver.resolve(q)
        payload = [x.model_dump() for x in campaigns]

        if not campaigns:
            return {
                **state,
                "campaigns": [],
                "status": "no_match",
                "route": "analytics -> campaign_resolution",
                "answer": (
                    "No campaign matched the supplied country/site, product, "
                    "and campaign context."
                ),
            }

        if len(campaigns) > 1:
            choices = "\n".join(
                f"- {x.campaign_id} — {x.campaign_name} "
                f"({x.campaign_start_date} to {x.campaign_end_date})"
                for x in campaigns
            )
            return {
                **state,
                "campaigns": payload,
                "status": "clarification",
                "route": "analytics -> campaign_resolution",
                "answer": (
                    "I found multiple matching campaigns. "
                    "Please choose one campaign_id:\n" + choices
                ),
            }

        campaign = campaigns[0]
        return {
            **state,
            "campaigns": payload,
            "resolved_campaign": campaign.model_dump(),
            "status": "resolved",
            "route": "analytics -> campaign_resolution",
        }

    def analytics_node(self, state: AgentState) -> AgentState:
        q = ReservationQuery(**state["query"])
        c = CampaignOption(**state["resolved_campaign"])
        result = self.analytics.query(
            campaign_id=c.campaign_id,
            user_id=q.user_id if state["metric"] == "user_reservation_check" else None,
        )

        answer = self._format_analytics_answer(
            metric=state["metric"],
            campaign=c,
            result=result,
        )

        return {
            **state,
            "analytics_result": result.model_dump(),
            "status": "answered",
            "route": f"analytics -> {getattr(self.analytics.backend, 'name', 'sql_backend')}",
            "answer": answer,
        }

    # -----------------------------
    # Routing
    # -----------------------------
    @staticmethod
    def after_extract(state: AgentState) -> str:
        return "knowledge" if state["intent"] == "knowledge" else "validate"

    @staticmethod
    def after_validate(state: AgentState) -> str:
        return "end" if state["status"] == "clarification" else "resolve_campaign"

    @staticmethod
    def after_campaign(state: AgentState) -> str:
        return "analytics" if state["status"] == "resolved" else "end"

    def _try_build_langgraph(self):
        try:
            from langgraph.graph import StateGraph, START, END
        except ImportError:
            return None

        builder = StateGraph(AgentState)
        builder.add_node("extract", self.extract_node)
        builder.add_node("knowledge", self.knowledge_node)
        builder.add_node("validate", self.validate_node)
        builder.add_node("resolve_campaign", self.resolve_campaign_node)
        builder.add_node("analytics", self.analytics_node)

        builder.add_edge(START, "extract")
        builder.add_conditional_edges(
            "extract",
            self.after_extract,
            {
                "knowledge": "knowledge",
                "validate": "validate",
            },
        )
        builder.add_edge("knowledge", END)

        builder.add_conditional_edges(
            "validate",
            self.after_validate,
            {
                "resolve_campaign": "resolve_campaign",
                "end": END,
            },
        )

        builder.add_conditional_edges(
            "resolve_campaign",
            self.after_campaign,
            {
                "analytics": "analytics",
                "end": END,
            },
        )

        builder.add_edge("analytics", END)
        return builder.compile()

    def invoke(
        self,
        question: str,
        prior_query: ReservationQuery | None = None,
        prior_metric: str | None = None,
    ) -> AgentState:
        initial: AgentState = {
            "question": question,
            "prior_query": prior_query.model_dump() if prior_query else None,
            "prior_metric": prior_metric,
            "debug": {
                "graph_runtime": "langgraph" if self._graph else "local-fallback",
            },
        }

        if self._graph is not None:
            return self._graph.invoke(initial)

        # Exact same logical route for offline demo when langgraph is not installed.
        state = self.extract_node(initial)
        if self.after_extract(state) == "knowledge":
            return self.knowledge_node(state)

        state = self.validate_node(state)
        if self.after_validate(state) == "end":
            return state

        state = self.resolve_campaign_node(state)
        if self.after_campaign(state) == "end":
            return state

        return self.analytics_node(state)

    @staticmethod
    def _format_analytics_answer(
        metric: str,
        campaign: CampaignOption,
        result: AnalyticsResult,
    ) -> str:
        prefix = f"{campaign.campaign_id} — {campaign.campaign_name}: "

        if metric == "reserved_users":
            return prefix + f"{result.reserved_users} reserved users."
        if metric == "ordered_users":
            return prefix + f"{result.ordered_users} ordered users."
        if metric == "reserved_not_ordered_users":
            return (
                prefix
                + f"{result.reserved_not_ordered_users} users reserved but did not order."
            )
        if metric == "conversion_rate":
            pct = (result.conversion_rate or 0.0) * 100
            return prefix + f"reservation-to-order conversion rate was {pct:.2f}%."
        if metric == "user_reservation_check":
            if not result.user_rows:
                return prefix + "no matching user-level reservation record was found."
            return prefix + f"found {len(result.user_rows)} matching user-level row(s): {result.user_rows}"

        pct = (result.conversion_rate or 0.0) * 100
        return (
            prefix
            + f"{result.reserved_users} reserved users, "
            f"{result.ordered_users} ordered users, "
            f"{result.reserved_not_ordered_users} reserved-but-not-ordered users, "
            f"and {pct:.2f}% conversion."
        )
