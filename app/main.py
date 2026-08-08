from fastapi import FastAPI
from pydantic import BaseModel

from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


settings = load_settings()
agent = ReservationAgent(settings, create_backend(settings))
app = FastAPI(title="Reservation Analytics AI Agent")


class AskRequest(BaseModel):
    question: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "backend": settings.backend}


@app.post("/ask")
def ask(request: AskRequest) -> dict:
    result = agent.invoke(request.question)
    return {
        "answer": result.get("answer", ""),
        "route": result.get("route", ""),
        "status": result.get("status", ""),
    }
