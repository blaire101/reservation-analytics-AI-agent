from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import ROOT, Settings


def build_agent() -> ReservationAgent:
    settings = Settings(
        app_env="test",
        backend="sqlite",
        knowledge_dir=ROOT / "knowledge",
        sqlite_path=ROOT / "local_data" / "reservation_analytics_test.db",
        use_llm=False,
        default_year=2026,
    )
    return ReservationAgent(settings, create_backend(settings))


def test_campaign_scope_includes_all_products():
    result = build_agent().invoke(
        "How many users reserved in Germany for CMP001?"
    )
    assert "9 reserved users" in result["answer"]


def test_product_scope_filters_one_product():
    result = build_agent().invoke(
        "How many users reserved Phone Mi 17 Pro in Germany for CMP001?"
    )
    assert "8 reserved users" in result["answer"]
