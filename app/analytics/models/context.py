"""Models for governed entity candidates and final resolved analytics context."""

from __future__ import annotations

from pydantic import BaseModel


class EntityCandidate(BaseModel):
    """One governed dimension-table candidate returned by name lookup.

    Example:
        entity_id='DE', name='Germany', description='Europe'
    """

    entity_id: str
    name: str
    description: str = ''


class CampaignContext(BaseModel):
    """Stable governed IDs that controlled SQL is allowed to use.

    This model is the boundary between fuzzy natural-language interpretation
    and deterministic analytics execution.
    """

    campaign_id: str
    campaign_name: str
    country_code: str
    country_name: str
    product_id: str | None = None
    product_name: str | None = None
