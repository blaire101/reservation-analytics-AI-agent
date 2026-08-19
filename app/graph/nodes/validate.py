"""Validation node: check whether analytics has enough business context."""

from app.analytics.models.request import ReservationQuery
from app.analytics.validation.validator import validate_business_plan


def run(state):
    """Validate the structured analytics query before entity resolution.

    Returns:
        If context is missing, return a clarification message.
        Otherwise mark the state as ``validated`` so LangGraph can continue to
        entity resolution.
    """
    query = ReservationQuery(**state['query'])
    message = validate_business_plan(query)

    if message:
        return {
            **state,
            'route': 'analytics',
            'status': 'clarification',
            'answer': message,
        }

    return {**state, 'status': 'validated'}
