import app.analytics.resolver as resolver_module
import app.core.extractor as extractor_module

from app.analytics.resolver import CampaignResolver
from app.analytics.service import AnalyticsService
from app.core.models import (
    ExtractedRequest,
    MatchDecision,
    ReservationQuery,
)
from app.data.backend import create_backend
from app.settings import ROOT, Settings


class FakeLLM:
    def __init__(self, mode: str):
        self.mode = mode

    def invoke(self, prompt: str):
        if self.mode == "extract":
            return ExtractedRequest(
                intent="analytics",
                metric="reserved_users",
                query=ReservationQuery(
                    country="Germany",
                    campaign_id="CMP001",
                ),
            )

        if "Germany" in prompt and '"DE"' in prompt:
            return MatchDecision(selected_id="DE")
        if "Mi 17 Pro" in prompt and '"P001"' in prompt:
            return MatchDecision(selected_id="P001")
        if "CMP001" in prompt and '"CMP001"' in prompt:
            return MatchDecision(selected_id="CMP001")

        return MatchDecision(candidate_ids=["CMP001", "CMP002"])


def settings() -> Settings:
    return Settings(
        app_env="test",
        backend="sqlite",
        knowledge_dir=ROOT / "knowledge",
        sqlite_path=ROOT / "local_data" / "reservation_analytics_test.db",
        openai_api_key="test-key",
    )


def backend():
    return create_backend(settings())


def patch_llms(monkeypatch):
    monkeypatch.setattr(
        extractor_module,
        "_build_llm",
        lambda _: FakeLLM("extract"),
    )
    monkeypatch.setattr(
        resolver_module,
        "_build_llm",
        lambda _: FakeLLM("resolve"),
    )


def test_extractor_uses_structured_llm(monkeypatch):
    patch_llms(monkeypatch)

    request = extractor_module.RequestExtractor(settings()).extract(
        "Germany CMP001 reserved users"
    )

    assert request.intent == "analytics"
    assert request.metric == "reserved_users"
    assert request.query.campaign_id == "CMP001"


def test_campaign_without_product_aggregates_all_products(monkeypatch):
    patch_llms(monkeypatch)

    result = CampaignResolver(backend(), settings()).resolve(
        ReservationQuery(
            country="Germany",
            campaign_id="CMP001",
        )
    )

    assert result.context.product_id is None
    answer = AnalyticsService(backend()).run(
        "reserved_users",
        result.context,
    )
    assert "9 reserved users" in answer


def test_product_filter_scopes_one_product(monkeypatch):
    patch_llms(monkeypatch)

    result = CampaignResolver(backend(), settings()).resolve(
        ReservationQuery(
            country="Germany",
            product="Mi 17 Pro",
            campaign_id="CMP001",
        )
    )

    assert result.context.product_id == "P001"
    answer = AnalyticsService(backend()).run(
        "reserved_users",
        result.context,
    )
    assert "8 reserved users" in answer


def test_missing_llm_fails_clearly():
    try:
        Settings(openai_api_key=None).require_llm()
    except RuntimeError as exc:
        assert "LLM service is unavailable" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
