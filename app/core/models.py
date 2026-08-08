from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel


class ReservationQuery(BaseModel):
    country: str | None = None
    site: str | None = None
    product: str | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_month: int | None = None
    campaign_year: int | None = None


class ExtractedRequest(BaseModel):
    intent: Literal["knowledge", "analytics"]
    metric: str = "summary"
    query: ReservationQuery = ReservationQuery()


class Campaign(BaseModel):
    campaign_id: str
    campaign_name: str
    country: str
    site: str
    product_id: str
    product_name: str
    campaign_start_date: str
    campaign_end_date: str


class AgentState(TypedDict, total=False):
    question: str
    extracted: dict
    intent: str
    metric: str
    query: dict
    campaign: dict
    status: str
    answer: str
    route: str
