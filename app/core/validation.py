from __future__ import annotations

from app.core.models import ReservationQuery


def missing_analytics_context(query: ReservationQuery) -> list[str]:
    """Require at least one business clue; let the resolver do the rest.

    Country, product, and campaign are all optional filters. Once the user gives
    any one of them, the resolver can query governed candidates and clarify if
    several campaigns remain.
    """

    has_business_context = any(
        [
            query.country,
            query.country_code,
            query.product,
            query.product_id,
            query.campaign_id,
            query.campaign_name,
            query.campaign_month,
            query.campaign_year,
        ]
    )
    return [] if has_business_context else ["campaign or other business context"]
