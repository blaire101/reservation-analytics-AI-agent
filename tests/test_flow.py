from pathlib import Path

from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import ROOT, Settings


def build_agent():
    settings = Settings(
        app_env="test",
        backend="sqlite",
        knowledge_dir=ROOT / "knowledge",
        sqlite_path=ROOT / "local_data" / "reservation_analytics_test.db",
        use_llm=False,
        default_year=2026,
    )
    return ReservationAgent(settings, create_backend(settings))


def test_knowledge_path():
    result = build_agent().invoke("What does reserved but not ordered mean?")
    assert result["route"] == "knowledge"
    assert "freserve_flag=1" in result["answer"]


def test_reserved_users():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro in Germany for CMP001?")
    assert "8 reserved users" in result["answer"]


def test_product_whitespace_normalization():
    result = build_agent().invoke("How many users reserved Mi     17 in Germany for CMP001?")
    # CMP001 is a Mi 17 Pro campaign, so a base Mi 17 product must not be silently upgraded.
    assert result["status"] in {"clarification", "not_found"}


def test_conversion_rate():
    result = build_agent().invoke("What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?")
    assert "62.50%" in result["answer"]


def test_detail_returns_hash_only():
    result = build_agent().invoke("Show users who reserved but did not order for Phone Mi 17 Pro in Germany for CMP001.")
    assert "HASH_U006" in result["answer"]
    assert " fuser_id: " not in result["answer"]


def test_missing_context():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro?")
    assert result["status"] == "clarification"
    assert "country" in result["answer"]


def test_ambiguous_campaign_then_memory_confirmation():
    agent = build_agent()
    first = agent.invoke(
        "How many users reserved Phone Mi 17 Pro in Germany in August 2026?",
        session_id="feishu-thread-1",
    )
    assert first["status"] == "clarification"
    assert first["pending_entity"] == "campaign"
    assert "CMP001" in first["answer"] and "CMP002" in first["answer"]

    second = agent.invoke("CMP001", session_id="feishu-thread-1")
    assert second["status"] == "answered"
    assert "8 reserved users" in second["answer"]


def test_fastapi_generates_session_id_when_missing(monkeypatch):
    from app import main as api_main

    class FakeAgent:
        def invoke(self, question: str, session_id: str):
            assert question == "hello"
            assert session_id.startswith("api-")
            return {"answer": "ok", "route": "knowledge", "status": "answered"}

    monkeypatch.setattr(api_main, "agent", FakeAgent())
    response = api_main.ask(api_main.AskRequest(question="hello"))
    assert response["session_id"].startswith("api-")
    assert response["answer"] == "ok"
