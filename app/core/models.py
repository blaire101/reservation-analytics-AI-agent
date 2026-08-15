from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """Natural-language business context plus stable IDs resolved by the application."""

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


class Campaign(BaseModel):
    campaign_id: str
    campaign_name: str
    product_id: str
    product_name: str
    country_code: str
    country_name: str
    start_time: str
    end_time: str


class EntityCandidate(BaseModel):
    """A governed dimension candidate. The LLM may select only from these IDs."""

    entity_id: str
    name: str
    description: str = ""


class EntitySelection(BaseModel):
    status: Literal["resolved", "ambiguous", "not_found"]
    selected_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class ResolutionResult(BaseModel):
    status: Literal["resolved", "clarification", "not_found"]
    query: ReservationQuery
    campaign: Campaign | None = None
    pending_entity: Literal["country", "product", "campaign"] | None = None
    candidates: list[EntityCandidate] = Field(default_factory=list)
    message: str = ""


class AgentState(TypedDict, total=False):
    question: str
    intent: str
    metric: str
    detail_requested: bool
    query: dict
    resolved_context: dict
    status: str
    answer: str
    route: str

    # Stateful clarification fields.
    session_id: str
    pending_entity: str
    candidates: list[dict]
