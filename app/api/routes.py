"""FastAPI routes for health checks and natural-language agent questions."""

from fastapi import APIRouter

from app.api.schemas import AskRequest, AskResponse


def build_router(get_agent):
    """Build the HTTP router used by the application.

    Args:
        get_agent: Callable that returns the shared ``ReservationAgent``.

    Returns:
        An ``APIRouter`` exposing ``GET /health`` and ``POST /ask``.

    Flow for /ask:
        HTTP request
            -> AskRequest validation
            -> ReservationAgent.invoke()
            -> LangGraph workflow
            -> AskResponse
    """
    router = APIRouter()

    @router.get('/health')
    def health():
        """Return a simple liveness response used by local checks or probes."""
        return {'status': 'ok'}

    @router.post('/ask', response_model=AskResponse)
    def ask(request: AskRequest):
        """Send one natural-language question through the agent workflow.

        Args:
            request: Validated API request containing ``request.question``.

        Returns:
            A small response containing the final answer, route, status, and
            optional entity candidates.
        """
        # Run the complete LangGraph workflow.
        result = get_agent().invoke(request.question)

        # Expose only the fields that are useful to an API client.
        return {
            'answer': result.get('answer', ''),
            'route': result.get('route', ''),
            'status': result.get('status', ''),
            'candidates': result.get('candidates', []),
        }

    return router
