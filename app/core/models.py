from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """Business context extracted from the question and enriched by the resolver."""

    country: str | None = None
    country_code: str | None = None

    product: str | None = None
    product_id: str | None = None

    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_month: int | None = None
    campaign_year: int | None = None


class ExtractedRequest(BaseModel):
    """Typed output produced by the request extractor."""

    intent: Literal["knowledge", "analytics"]
    metric: str = "summary"
    detail_requested: bool = False
    query: ReservationQuery = Field(default_factory=ReservationQuery)


class Campaign(BaseModel):
    """One fully resolved Campaign + Product + Country context."""

    campaign_id: str
    campaign_name: str
    product_id: str
    product_name: str
    country_code: str
    country_name: str
    start_time: str
    end_time: str


class EntityCandidate(BaseModel):
    """One governed dimension candidate shown to the selector or user."""

    entity_id: str
    name: str
    description: str = ""


class EntitySelection(BaseModel):
    """Selector decision over a governed candidate list."""

    status: Literal["resolved", "ambiguous", "not_found"]
    selected_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)
    reason: str = ""


class ResolutionResult(BaseModel):
    """Business-context resolution result returned to the graph."""

    status: Literal["resolved", "clarification", "not_found"]
    query: ReservationQuery
    campaign: Campaign | None = None
    pending_entity: Literal["country", "product", "campaign"] | None = None
    candidates: list[EntityCandidate] = Field(default_factory=list)
    message: str = ""


class AgentState(TypedDict, total=False):
    """Small state passed between LangGraph nodes and clarification turns."""

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
