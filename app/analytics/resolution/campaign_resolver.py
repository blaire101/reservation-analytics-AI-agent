"""Resolve campaign context using governed dimensions and already-resolved IDs."""

from app.analytics.models.request import ReservationQuery
from app.analytics.resolution.repository import DimensionRepository


def resolve_campaign(query: ReservationQuery, repo: DimensionRepository):
    """Resolve the final campaign and return stable analytics context.

    Returns:
        Tuple ``(status, context, candidates)``.

    Rules:
        Explicit campaign_id:
            Validate it directly together with any known country/product IDs.
        Natural-language campaign context:
            Search governed campaign candidates using country, product, name,
            year, and month filters. Exactly one candidate is required.

    Important:
        A stable campaign ID never goes through LLM/name resolution again.
    """
    # Fast deterministic path for an explicit stable ID.
    if query.campaign_id:
        context = repo.campaign_context_by_id(
            query.campaign_id,
            query.country_code,
            query.product_id,
        )
        return ('ok', context, []) if context else ('not_found', None, [])

    # Natural-language path: narrow the governed campaign dimension.
    matches = repo.campaigns_by_context(query)

    if len(matches) == 1:
        chosen = matches[0]
        context = repo.campaign_context_by_id(
            chosen.entity_id,
            query.country_code,
            query.product_id,
        )
        return ('ok', context, matches) if context else ('not_found', None, [])

    if matches:
        return ('ambiguous', None, matches)
    return ('not_found', None, [])
