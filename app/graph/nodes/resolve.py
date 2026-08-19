"""Resolution node: convert business wording into stable governed IDs."""

from app.analytics.models.request import ReservationQuery


def run(resolver, state):
    """Resolve country/product/campaign context for controlled analytics.

    Resolution rule:
        Stable ID supplied -> exact validation only.
        Natural-language name supplied -> governed dimension lookup.

    Returns:
        - ``resolved`` with ``resolved_context`` when one valid context exists.
        - ``clarification`` with candidates when a name is ambiguous.
        - ``not_found`` when no governed entity matches.
    """
    query = ReservationQuery(**state['query'])
    result = resolver.resolve(query)

    # Keep the normalized query in state so later steps can inspect it.
    base = {
        **state,
        'route': 'analytics',
        'status': result.status,
        'query': result.query.model_dump(),
    }

    if result.status == 'resolved' and result.context:
        return {
            **base,
            'resolved_context': result.context.model_dump(),
        }

    # Stop the analytics path and return clarification/not-found information.
    return {
        **base,
        'answer': result.message,
        'candidates': [candidate.model_dump() for candidate in result.candidates],
    }
