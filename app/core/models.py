from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """Business wording extracted from the user and enriched by the resolver."""

    country: str | None = None
    country_code: str | None = None

    product: str | None = None
    product_id: str | None = None

    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_month: int | None = None
    campaign_year: int | None = None


class ExtractedRequest(BaseModel):
    intent: Literal["knowledge", "analytics"]
    metric: str = "summary"
    detail_requested: bool = False
    query: ReservationQuery = Field(default_factory=ReservationQuery)


class CampaignContext(BaseModel):
    """Stable context used by analytics.

    A campaign may contain many products, so product_id is optional.
    If product_id is None, analytics aggregates all products in the campaign.
    """

    campaign_id: str
    campaign_name: str
    country_code: str
    country_name: str
    product_id: str | None = None
    product_name: str | None = None


class EntityCandidate(BaseModel):
    entity_id: str
    name: str
    description: str = ""


class ResolutionResult(BaseModel):
    status: Literal["resolved", "clarification", "not_found"]
    query: ReservationQuery
    context: CampaignContext | None = None
    pending_entity: Literal["country", "product", "campaign"] | None = None
    candidates: list[EntityCandidate] = Field(default_factory=list)
    message: str = ""


class AgentState(TypedDict, total=False):
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
