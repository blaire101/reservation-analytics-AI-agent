from app.analytics.models.request import ReservationQuery
from app.analytics.query.backend import create_backend
from app.analytics.resolution.service import BusinessResolver
from app.analytics.service import AnalyticsService
from app.settings import ROOT, Settings


def settings():
    return Settings(
        app_env='test', backend='sqlite', knowledge_dir=ROOT/'knowledge',
        sqlite_path=ROOT/'local_data'/'reservation_analytics_test_v7.db',
        openai_api_key='test-key',
    )


def backend(): return create_backend(settings())


def test_stable_campaign_id_goes_directly_to_exact_context():
    result = BusinessResolver(backend()).resolve(
        ReservationQuery(campaign_id='CMP001', country_code='DE')
    )
    assert result.status == 'resolved'
    assert result.context.campaign_id == 'CMP001'


def test_natural_language_names_resolve_to_governed_ids():
    result = BusinessResolver(backend()).resolve(
        ReservationQuery(campaign_name='Mi 17 Launch', country='Germany')
    )
    assert result.status == 'resolved'
    assert result.context.campaign_id == 'CMP001'
    assert result.context.country_code == 'DE'


def test_product_name_scopes_metric():
    result = BusinessResolver(backend()).resolve(
        ReservationQuery(campaign_id='CMP001', country='Germany', product='Phone Mi 17 Pro')
    )
    answer = AnalyticsService(backend()).run('reserved_users', result.context)
    assert '8 reserved users' in answer


def test_invalid_id_returns_not_found():
    result = BusinessResolver(backend()).resolve(ReservationQuery(campaign_id='BAD999'))
    assert result.status == 'not_found'
