from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """Business wording extracted from the user."""

    country: str | None = None
    country_code: str | None = None

    product: str | None = None
    product_id: str | None = None

    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_month: int | None = None
    campaign_year: int | None = None

    def has_business_context(self) -> bool:
        """Return True when the user supplied at least one business clue."""

        return any(
            value is not None
            for value in (
                self.country,
                self.country_code,
                self.product,
                self.product_id,
                self.campaign_id,
                self.campaign_name,
                self.campaign_month,
                self.campaign_year,
            )
        )


class ExtractedRequest(BaseModel):
    """Structured output produced by the LLM."""

    intent: Literal["knowledge", "analytics"]
    metric: Literal[
        "summary",
        "reserved_users",
        "ordered_users",
        "reserved_not_ordered",
        "conversion_rate",
    ] = "summary"
    detail_requested: bool = False
    query: ReservationQuery = Field(default_factory=ReservationQuery)


class CampaignContext(BaseModel):
    """Stable context passed to controlled analytics SQL.

    A campaign may contain many products.
    product_id=None means campaign-level analytics across all products.
    """

    campaign_id: str
    campaign_name: str
    country_code: str
    country_name: str
    product_id: str | None = None
    product_name: str | None = None


class EntityCandidate(BaseModel):
    """One governed candidate returned by a dimension table."""

    entity_id: str
    name: str
    description: str = ""


class MatchDecision(BaseModel):
    """LLM decision restricted to governed candidate IDs."""

    selected_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)


class ResolutionResult(BaseModel):
    status: Literal["resolved", "clarification", "not_found"]
    query: ReservationQuery
    context: CampaignContext | None = None
    pending_entity: Literal["country", "product", "campaign"] | None = None
    candidates: list[EntityCandidate] = Field(default_factory=list)
    message: str = ""


class AgentState(TypedDict, total=False):
    """Shared LangGraph state."""

    question: str
    session_id: str

    intent: str
    metric: str
    detail_requested: bool
    query: dict

    route: str
    status: str
    answer: str
    resolved_context: dict

    pending_entity: str
    candidates: list[dict]
