from __future__ import annotations

from app.core.models import Campaign, ReservationQuery
from app.data.backend import QueryBackend


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def missing_context(query: ReservationQuery) -> list[str]:
    if query.campaign_id:
        return []
    missing: list[str] = []
    if not (query.country or query.country_code):
        missing.append("country")
    if not query.product:
        missing.append("product")
    if not (query.campaign_name or query.campaign_month):
        missing.append("campaign")
    return missing


class CampaignResolver:
    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def resolve(self, query: ReservationQuery) -> list[Campaign]:
        filters = ["1=1"]
        if query.campaign_id:
            filters.append(f"c.fcampaign_id = {_quote(query.campaign_id)}")
        if query.country:
            filters.append(f"lower(s.fcountry_name) = lower({_quote(query.country)})")
        if query.country_code:
            filters.append(f"lower(c.fcountry_code) = lower({_quote(query.country_code)})")
        if query.product:
            filters.append(f"lower(p.fproduct_name) LIKE lower({_quote('%' + query.product + '%')})")
        if query.campaign_name:
            filters.append(f"lower(c.fcampaign_name) LIKE lower({_quote('%' + query.campaign_name + '%')})")
        if query.campaign_year:
            filters.append(f"substr(c.fstart_time, 1, 4) = {_quote(str(query.campaign_year))}")
        if query.campaign_month:
            filters.append(f"substr(c.fstart_time, 6, 2) = {_quote(f'{query.campaign_month:02d}')}")

        sql = f"""
        SELECT
            c.fcampaign_id AS campaign_id,
            c.fcampaign_name AS campaign_name,
            c.fproduct_id AS product_id,
            p.fproduct_name AS product_name,
            c.fcountry_code AS country_code,
            s.fcountry_name AS country_name,
            c.fstart_time AS start_time,
            c.fend_time AS end_time
        FROM dim_campaign_df c
        JOIN dim_product_df p ON c.fproduct_id = p.fproduct_id
        JOIN dim_site_df s ON c.fcountry_code = s.fcountry_code
        WHERE {' AND '.join(filters)}
        ORDER BY c.fstart_time, c.fcampaign_id
        LIMIT 20
        """.strip()
        return [Campaign(**row) for row in self.backend.execute(sql)]
