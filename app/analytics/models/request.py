"""Pydantic models for the LLM's structured business plan."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class ReservationQuery(BaseModel):
    """Business entities and time clues extracted from the user question.

    Important rule:
        ``*_id`` / ``country_code`` fields should be populated only when the
        user explicitly provides a stable ID/code. Natural-language wording
        stays in the corresponding name field and is resolved later.
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
        """Return True when at least one business clue was extracted.

        Returns:
            ``True`` if country, product, campaign, or time information exists;
            otherwise ``False``.
        """
        return any(value is not None for value in self.model_dump().values())


class ExtractedRequest(BaseModel):
    """Small typed plan produced by the LLM before LangGraph routing.

    The object contains business intent only. It intentionally contains no SQL.
    """

    # Decide which controlled path should answer the question.
    intent: Literal['knowledge', 'analytics']

    # Analytics metric must come from this small allowlisted vocabulary.
    metric: Literal[
        'summary',
        'reserved_users',
        'ordered_users',
        'reserved_not_ordered',
        'conversion_rate',
    ] = 'summary'

    # True when the user wants individual detail records rather than a summary.
    detail_requested: bool = False

    # Extracted business context.
    query: ReservationQuery = Field(default_factory=ReservationQuery)
