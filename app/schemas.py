from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


MetricName = Literal[
    "reserved_users",
    "ordered_users",
    "reserved_not_ordered_users",
    "conversion_rate",
    "campaign_summary",
    "user_reservation_check",
]


class ReservationQuery(BaseModel):
    # Core business context requested by the project design.
    country: str | None = None
    site: str | None = None
    product: str | None = None
    campaign_id: str | None = None
    campaign_name: str | None = None
    campaign_start_date: str | None = None
    campaign_end_date: str | None = None

    # Optional extension for natural phrases such as "the August campaign".
    campaign_month: int | None = Field(default=None, ge=1, le=12)
    campaign_year: int | None = None

    # Only needed for user-level checks.
    user_id: str | None = None


class ExtractedRequest(BaseModel):
    intent: Literal["knowledge", "analytics"]
    metric: MetricName = "campaign_summary"
    query: ReservationQuery
    reasoning_summary: str = ""


class CampaignOption(BaseModel):
    campaign_id: str
    campaign_name: str
    country: str
    site: str
    product_id: str | None = None
    product_name: str
    campaign_start_date: str
    campaign_end_date: str


class AnalyticsResult(BaseModel):
    campaign_id: str
    reserved_users: int | None = None
    ordered_users: int | None = None
    reserved_not_ordered_users: int | None = None
    conversion_rate: float | None = None
    user_rows: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    route: str
    status: Literal["answered", "clarification", "no_match", "error"]
    extracted: ReservationQuery | None = None
    resolved_campaign: CampaignOption | None = None
    metric: MetricName | None = None
    debug: dict = Field(default_factory=dict)
