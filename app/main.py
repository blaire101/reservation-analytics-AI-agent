from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


settings = load_settings()
app = FastAPI(title="Reservation Analytics AI Agent")
_agent: ReservationAgent | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    session_id: str | None = None


class AskResponse(BaseModel):
    answer: str
    route: str
    status: str
    session_id: str
    pending_entity: str = ""
    candidates: list[dict] = Field(default_factory=list)


def get_agent() -> ReservationAgent:
    """Create the Agent once; LLM is a required dependency."""

    global _agent
    if _agent is None:
        _agent = ReservationAgent(
            settings,
            create_backend(settings),
        )
    return _agent


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "backend": settings.backend,
        "llm_configured": bool(settings.openai_api_key),
    }


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    """Run one message; reuse session_id for clarification replies."""

    session_id = request.session_id or f"api-{uuid4().hex}"

    try:
        result = get_agent().invoke(
            request.question,
            session_id=session_id,
        )
    except RuntimeError as exc:
        return {
            "answer": str(exc),
            "route": "",
            "status": "unavailable",
            "session_id": session_id,
            "pending_entity": "",
            "candidates": [],
        }

    return {
        "answer": result.get("answer", ""),
        "route": result.get("route", ""),
        "status": result.get("status", ""),
        "session_id": session_id,
        "pending_entity": result.get("pending_entity", ""),
        "candidates": result.get("candidates", []),
    }
