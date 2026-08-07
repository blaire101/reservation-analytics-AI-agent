from __future__ import annotations

from fastapi import FastAPI

from app.agent_service import ReservationAgentService
from app.config import AppSettings
from app.schemas import ChatRequest, ChatResponse


settings = AppSettings()
service = ReservationAgentService(settings)

app = FastAPI(
    title="Reservation Analytics AI Agent",
    version="2.0.0",
    description=(
        "AI layer over a configurable Reservation Data Mart backend. "
        "Default local mode uses SQLite; enterprise backends can use Athena "
        "or an internal SQL gateway."
    ),
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "mock_mode": settings.mock_mode,
        "data_backend": service.backend.name,
        "region": settings.data_region,
        "cluster": settings.data_cluster,
        "dm": f"{settings.dm_database}.{settings.dm_table}",
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    return service.chat(req.message, req.session_id)


@app.post("/reset/{session_id}")
def reset(session_id: str):
    service.reset(session_id)
    return {"status": "reset", "session_id": session_id}


@app.get("/examples")
def examples():
    return {
        "knowledge": [
            "What does reserved-but-not-ordered mean?",
            "How is reservation-to-order conversion rate calculated?",
        ],
        "analytics": [
            "How many users reserved Xiaomi 17 Pro in Germany for CMP001 but did not order?",
            "What was the conversion rate for Xiaomi 17 Pro in Germany for CMP001?",
        ],
        "clarification": [
            "How many users reserved Xiaomi 17 Pro?",
            "Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.",
        ],
    }
