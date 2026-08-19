"""Resolve country context using governed dimension data."""

from app.analytics.models.request import ReservationQuery
from app.analytics.resolution.repository import DimensionRepository


def resolve_country(query: ReservationQuery, repo: DimensionRepository):
    """Validate a stable country code or resolve a natural-language name.

    Args:
        query: Structured business query.
        repo: Repository that reads governed dimension tables.

    Returns:
        Tuple ``(status, candidates)`` where status is ``ok``, ``ambiguous``,
        or ``not_found``.

    Rules:
        1. Explicit ``country_code`` -> exact validation; no fuzzy resolution.
        2. No country clue -> optional dimension, so continue with no candidate.
        3. Natural-language country -> governed name lookup.
    """
    # Stable code: validate exactly against the governed dimension table.
    if query.country_code:
        item = repo.country_by_code(query.country_code)
        return ('not_found', []) if not item else ('ok', [item])

    # Country is optional at this stage.
    if not query.country:
        return ('ok', [])

    # Name: resolution is needed because natural language may be ambiguous.
    matches = repo.countries_by_name(query.country)

    if len(matches) == 1:
        return ('ok', matches)
    if matches:
        return ('ambiguous', matches)
    return ('not_found', [])
