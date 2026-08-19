"""Resolve product context using governed dimension data."""

from app.analytics.models.request import ReservationQuery
from app.analytics.resolution.repository import DimensionRepository


def resolve_product(query: ReservationQuery, repo: DimensionRepository):
    """Validate a stable product ID or resolve a natural-language product name.

    Rules:
        Explicit product_id -> exact validation.
        Product name -> governed name lookup.
        No product clue -> continue because product is optional.
    """
    # Stable ID bypasses semantic/name resolution.
    if query.product_id:
        item = repo.product_by_id(query.product_id)
        return ('not_found', []) if not item else ('ok', [item])

    if not query.product:
        return ('ok', [])

    matches = repo.products_by_name(query.product)

    if len(matches) == 1:
        return ('ok', matches)
    if matches:
        return ('ambiguous', matches)
    return ('not_found', [])
