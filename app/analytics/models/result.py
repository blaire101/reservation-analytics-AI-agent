"""Models returned by the governed entity-resolution layer."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

from app.analytics.models.context import CampaignContext, EntityCandidate
from app.analytics.models.request import ReservationQuery


class ResolutionResult(BaseModel):
    """Represent the outcome of country/product/campaign resolution.

    Status meanings:
        resolved:
            Exactly one governed context was found and controlled SQL may run.
        clarification:
            Multiple governed candidates matched; the caller should ask for a
            stable ID or more specific wording.
        not_found:
            No governed entity matched the request.
    """

    status: Literal['resolved', 'clarification', 'not_found']
    query: ReservationQuery
    context: CampaignContext | None = None
    candidates: list[EntityCandidate] = Field(default_factory=list)
    message: str = ''
