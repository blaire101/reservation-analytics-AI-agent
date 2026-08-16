from app.analytics.resolver import CampaignResolver
from app.core.graph import ReservationAgent
from app.core.models import ReservationQuery
from app.data.backend import create_backend
from app.settings import ROOT, Settings


def build_settings() -> Settings:
    return Settings(
        app_env="test",
        backend="sqlite",
        knowledge_dir=ROOT / "knowledge",
        sqlite_path=ROOT / "local_data" / "reservation_analytics_test.db",
        use_llm=False,
        default_year=2026,
    )


def build_agent() -> ReservationAgent:
    settings = build_settings()
    return ReservationAgent(settings, create_backend(settings))


def test_knowledge_path():
    result = build_agent().invoke("What does reserved but not ordered mean?")
    assert result["route"] == "knowledge"
    assert "freserve_flag=1" in result["answer"]


def test_reserved_users():
    result = build_agent().invoke(
        "How many users reserved Phone Mi 17 Pro in Germany for CMP001?"
    )
    assert "8 reserved users" in result["answer"]


def test_campaign_id_can_derive_product_when_product_is_missing():
    result = build_agent().invoke(
        "How many users reserved in Germany for CMP001?"
    )
    assert result["status"] == "answered"
    assert "8 reserved users" in result["answer"]


def test_campaign_name_can_derive_product_when_product_is_missing():
    settings = build_settings()
    backend = create_backend(settings)
    resolver = CampaignResolver(backend, settings)

    result = resolver.resolve(
        ReservationQuery(
            country="Germany",
            campaign_name="Phone Mi 17 Pro Launch",
        )
    )

    assert result.status == "resolved"
    assert result.campaign is not None
    assert result.campaign.campaign_id == "CMP001"
    assert result.query.product_id == "P001"



def test_country_and_product_without_campaign_returns_governed_campaign_choices():
    result = build_agent().invoke(
        "How many users reserved Phone Mi 17 Pro in Germany?"
    )
    assert result["status"] == "clarification"
    assert result["pending_entity"] == "campaign"
    assert "CMP001" in result["answer"] and "CMP002" in result["answer"]


def test_no_business_context_is_rejected_before_resolution():
    result = build_agent().invoke("How many reservations?")
    assert result["status"] == "clarification"
    assert "business context" in result["answer"]

def test_product_whitespace_normalization():
    result = build_agent().invoke(
        "How many users reserved Mi     17 in Germany for CMP001?"
    )
    # CMP001 belongs to the Pro product, so the base model must not be silently upgraded.
    assert result["status"] in {"clarification", "not_found"}


def test_conversion_rate():
    result = build_agent().invoke(
        "What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?"
    )
    assert "62.50%" in result["answer"]


def test_detail_returns_hash_only():
    result = build_agent().invoke(
        "Show users who reserved but did not order for Phone Mi 17 Pro in Germany for CMP001."
    )
    assert "HASH_U006" in result["answer"]
    assert " fuser_id: " not in result["answer"]


def test_missing_campaign_context():
    result = build_agent().invoke("How many users reserved Phone Mi 17 Pro?")
    assert result["status"] == "clarification"
    assert "campaign" in result["answer"]


def test_ambiguous_campaign_then_memory_confirmation():
    agent = build_agent()
    first = agent.invoke(
        "How many users reserved Phone Mi 17 Pro in Germany in August 2026?",
        session_id="feishu-thread-1",
    )
    assert first["status"] == "clarification"
    assert first["pending_entity"] == "campaign"
    assert "CMP001" in first["answer"] and "CMP002" in first["answer"]

    second = agent.invoke("1", session_id="feishu-thread-1")
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
