"""Simple validation rules for the structured analytics business plan."""

from app.analytics.models.request import ReservationQuery


def validate_business_plan(query: ReservationQuery) -> str | None:
    """Check whether entity resolution has at least one business clue.

    Args:
        query: Structured country/product/campaign context extracted by the LLM.

    Returns:
        ``None`` when the request can continue, otherwise a short clarification
        message for the user.

    Why this is separate:
        Validation is deterministic application logic. It prevents an empty
        analytics request from reaching entity resolution or SQL execution.
    """
    if query.has_business_context():
        return None

    return 'Please provide a campaign, product, country, or other business context.'
