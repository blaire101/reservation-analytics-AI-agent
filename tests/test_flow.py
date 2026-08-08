from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


def build_agent():
    settings = load_settings("config/local.env")
    return ReservationAgent(settings, create_backend(settings))


def test_knowledge_path():
    result = build_agent().invoke("What does reserved but not ordered mean?")
    assert result["route"] == "knowledge"
    assert "freserve_flag=1" in result["answer"]


def test_reserved_users():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro in Germany for CMP001?")
    assert "8 reserved users" in result["answer"]


def test_conversion_rate():
    result = build_agent().invoke("What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?")
    assert "62.50%" in result["answer"]


def test_detail_returns_hash_only():
    result = build_agent().invoke("Show users who reserved but did not order for Phone Mi 17 Pro in Germany for CMP001.")
    assert "HASH_U006" in result["answer"]
    assert " fuser_id: " not in result["answer"]
    assert "raw user" not in result["answer"].lower()


def test_missing_context():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro?")
    assert result["status"] == "clarification"
    assert "country" in result["answer"]


def test_ambiguous_campaign():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro in Germany in August 2026?")
    assert result["status"] == "clarification"
    assert "CMP001" in result["answer"] and "CMP002" in result["answer"]
