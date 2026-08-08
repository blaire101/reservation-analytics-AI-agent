from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """
    Structured business filters extracted from the user's natural-language query.
    Example:
        "How many users reserved Phone Mi 17 Pro in Germany for the August launch campaign?"
    May be extracted as:
        country="Germany"
        product="Phone Mi 17 Pro"
        campaign_name="August launch"
    """

    country: str | None = None
    country_code: str | None = None

    product: str | None = None

    campaign_id: str | None = None
    campaign_name: str | None = None

    campaign_month: int | None = None
    campaign_year: int | None = None


class ExtractedRequest(BaseModel):
    """
    Structured output produced after the LLM understands the user question.

    It answers four things:

    1. intent
       Is this a knowledge question or an analytics question?
    2. metric
       Which metric or result does the user want?
    3. detail_requested
       Does the user want aggregate metrics or detail-level records?
    4. query
       What business filters were extracted from the question?
    """

    intent: Literal["knowledge", "analytics"]

    # Examples:
    # summary, reserved_users, ordered_users,
    # reserved_not_ordered, conversion_rate
    metric: str = "summary"

    # False -> aggregate result
    # True  -> detail-level records
    detail_requested: bool = False

    query: ReservationQuery = Field(default_factory=ReservationQuery)


class Campaign(BaseModel):
    """
    Resolved campaign context used by the analytics path.

    The resolver converts natural-language business context into
    one unambiguous Campaign + Product + Site/Country combination.

    Application-layer field names stay clean here.
    Warehouse columns may use names such as:
        fcampaign_id
        fproduct_id
        fcountry_code
    """

    campaign_id: str
    campaign_name: str

    product_id: str
    product_name: str

    country_code: str
    country_name: str

    start_time: str
    end_time: str


class AgentState(TypedDict, total=False):
    """
    Shared working state passed through the LangGraph workflow.

    Each LangGraph node reads values from this state and may add or
    update values before passing the state to the next node.

    Typical flow:

        question
            ↓
        extraction
            ↓
        intent / metric / query
            ↓
        business context resolution
            ↓
        knowledge or analytics path
            ↓
        answer
    """

    # Original user question.
    question: str

    # Question type: knowledge or analytics.
    intent: str

    # Requested metric, e.g. reserved_users or conversion_rate.
    metric: str

    # True when the user requests detail-level records.
    detail_requested: bool

    # Business filters extracted from the natural-language question.
    query: dict

    # Resolved Campaign + Product + Country context.
    resolved_context: dict

    # Workflow result:
    # success / not_found / clarification / error
    status: str

    # Final user-facing response.
    answer: str

    # Routing target used by LangGraph conditional edges.
    route: str
