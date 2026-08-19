"""Analytics node: execute application-controlled metric SQL."""

from app.analytics.models.context import CampaignContext


def run(service, state):
    """Execute the selected metric against the resolved governed context.

    Args:
        service: ``AnalyticsService`` that owns allowlisted metric logic.
        state: LangGraph state containing metric and ``resolved_context``.

    Returns:
        Updated state with the trusted analytics answer.

    Important:
        The LLM is no longer involved here. SQL is selected/built by
        application code from the allowlisted metric definitions.
    """
    context = CampaignContext(**state['resolved_context'])

    answer = service.run(
        state['metric'],
        context,
        state.get('detail_requested', False),
    )

    return {
        **state,
        'route': 'analytics',
        'status': 'answered',
        'answer': answer,
    }
