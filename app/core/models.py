from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


# ==========================================================
# 1. LLM output
# ==========================================================

class ExtractedRequest(BaseModel):
    """
    Structured request returned by the LLM.

    question
      → intent
      → metric
      → ReservationQuery
    """

    intent: Literal[
        "knowledge",
        "analytics",
    ]

    metric: Literal[
        "summary",
        "reserved_users",
        "ordered_users",
        "reserved_not_ordered",
        "conversion_rate",
    ] = "summary"

    detail_requested: bool = False

    query: "ReservationQuery" = Field(
        default_factory=lambda: ReservationQuery()
    )


# ==========================================================
# 2. User business context
# ==========================================================

class ReservationQuery(BaseModel):
    """
    Business entities extracted from the user.

    Natural-language fields:
        country
        product
        campaign_name

    Stable governed fields:
        country_code
        product_id
        campaign_id
    """

    country: str | None = None
    country_code: str | None = None

    product: str | None = None
    product_id: str | None = None

    campaign_name: str | None = None
    campaign_id: str | None = None

    campaign_month: int | None = None
    campaign_year: int | None = None

    def has_business_context(self) -> bool:
        """True when analytics has at least one business clue."""

        return any(
            value is not None
            for value in (
                self.country,
                self.country_code,
                self.product,
                self.product_id,
                self.campaign_name,
                self.campaign_id,
                self.campaign_month,
                self.campaign_year,
            )
        )


# Rebuild the forward reference used by ExtractedRequest.
ExtractedRequest.model_rebuild()


# ==========================================================
# 3. Governed dimension candidates
# ==========================================================

class EntityCandidate(BaseModel):
    """One candidate returned from a governed dimension table."""

    entity_id: str
    name: str
    description: str = ""


class MatchDecision(BaseModel):
    """
    LLM decision for governed candidates.

    Unique:
        selected_id = "CMP001"

    Ambiguous:
        selected_id = None
        candidate_ids = ["CMP001", "CMP002"]
    """

    selected_id: str | None = None

    candidate_ids: list[str] = Field(
        default_factory=list
    )


# ==========================================================
# 4. Final stable analytics context
# ==========================================================

class CampaignContext(BaseModel):
    """
    Stable IDs used by AnalyticsService.

    Product is optional:
        product_id=None
        → aggregate all products in the campaign.
    """

    campaign_id: str
    campaign_name: str

    country_code: str
    country_name: str

    product_id: str | None = None
    product_name: str | None = None


# ==========================================================
# 5. Resolver output
# ==========================================================

class ResolutionResult(BaseModel):
    """
    Result returned by CampaignResolver.

    resolved:
        context is ready for analytics

    clarification:
        ask the user to choose a candidate

    not_found:
        stop without running analytics SQL
    """

    status: Literal[
        "resolved",
        "clarification",
        "not_found",
    ]

    query: ReservationQuery

    context: CampaignContext | None = None

    pending_entity: Literal[
        "country",
        "product",
        "campaign",
    ] | None = None

    candidates: list[EntityCandidate] = Field(
        default_factory=list
    )

    message: str = ""


# ==========================================================
# 6. LangGraph shared state
# ==========================================================

class AgentState(TypedDict, total=False):
    """Shared state passed between LangGraph nodes."""

    # Request
    question: str
    session_id: str

    # Extracted request
    intent: str
    metric: str
    detail_requested: bool
    query: dict

    # Workflow result
    route: str
    status: str
    answer: str

    # Resolved analytics context
    resolved_context: dict

    # Multi-turn clarification
    pending_entity: str
    candidates: list[dict]
