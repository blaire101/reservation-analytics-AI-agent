from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


settings = load_settings()
agent = ReservationAgent(settings, create_backend(settings))
app = FastAPI(title="Reservation Analytics AI Agent")


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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backend": settings.backend}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    """Run one question; reuse session_id when replying to a clarification."""

    session_id = request.session_id or f"api-{uuid4().hex}"
    result = agent.invoke(request.question, session_id=session_id)

    return {
        "answer": result.get("answer", ""),
        "route": result.get("route", ""),
        "status": result.get("status", ""),
        "session_id": session_id,
        "pending_entity": result.get("pending_entity", ""),
        "candidates": result.get("candidates", []),
    }
