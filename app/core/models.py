from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    country: str | None = None
    country_code: str | None = None
    product: str | None = None
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


class AgentState(TypedDict, total=False):
    question: str
    extracted: dict
    intent: str
    metric: str
    detail_requested: bool
    query: dict
    campaign: dict
    status: str
    answer: str
    route: str
