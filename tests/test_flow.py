from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


def build_agent():
    settings = load_settings("config/default.env")
    return ReservationAgent(settings, create_backend(settings))


def test_knowledge_path():
    result = build_agent().invoke("What does reserved but not ordered mean?")
    assert result["route"] == "knowledge"
    assert "no matching order" in result["answer"]


def test_reserved_users():
    result = build_agent().invoke(
        "How many users reserved Phone Mi 17 Pro in Germany for CMP001?"
    )
    assert result["route"] == "analytics"
    assert "8 reserved users" in result["answer"]


def test_conversion_rate():
    result = build_agent().invoke(
        "What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?"
    )
    assert "62.50%" in result["answer"]


def test_missing_context():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro?")
    assert result["status"] == "clarification"
    assert "country or site" in result["answer"]


def test_ambiguous_campaign():
    result = build_agent().invoke(
        "How many users reserved Phone Mi 17 Pro in Germany in August 2026?"
    )
    assert result["status"] == "clarification"
    assert "CMP001" in result["answer"]
    assert "CMP002" in result["answer"]
