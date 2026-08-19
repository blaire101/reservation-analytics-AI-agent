"""FastAPI application entry point.

This file connects the main application pieces:

    Settings -> QueryBackend -> ReservationAgent -> FastAPI routes

The agent is created lazily and reused across API requests so the RAG index and
other dependencies do not need to be rebuilt for every question.
"""

from fastapi import FastAPI

from app.analytics.query.backend import create_backend
from app.api.routes import build_router
from app.graph.workflow import ReservationAgent
from app.settings import load_settings

# Load configuration once when the application starts.
settings = load_settings()

# Create the FastAPI application object used by Uvicorn.
app = FastAPI(title='Reservation Analytics AI Agent')

# The agent is created on the first request and then reused.
_agent = None


def get_agent():
    """Create and cache the ReservationAgent used by API requests.

    Returns:
        A ready-to-use ``ReservationAgent`` connected to the configured query
        backend.

    Flow:
        Settings
            -> create_backend()
            -> ReservationAgent
            -> cached in _agent
    """
    global _agent

    # Lazy initialization avoids constructing the LLM/RAG stack before it is
    # actually needed.
    if _agent is None:
        backend = create_backend(settings)
        _agent = ReservationAgent(settings, backend)

    return _agent


# Register /health and /ask endpoints.
app.include_router(build_router(get_agent))
