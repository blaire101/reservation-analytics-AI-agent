from __future__ import annotations

from app.core.models import Campaign, ReservationQuery
from app.data.backend import QueryBackend


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def missing_context(query: ReservationQuery) -> list[str]:
    if query.campaign_id:
        return []

    missing: list[str] = []
    if not (query.country or query.site):
        missing.append("country or site")
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
            filters.append(f"campaign_id = {_quote(query.campaign_id)}")
        if query.country:
            filters.append(f"lower(country) = lower({_quote(query.country)})")
        if query.site:
            filters.append(f"lower(site) = lower({_quote(query.site)})")
        if query.product:
            filters.append(f"lower(product_name) LIKE lower({_quote('%' + query.product + '%')})")
        if query.campaign_name:
            filters.append(f"lower(campaign_name) LIKE lower({_quote('%' + query.campaign_name + '%')})")
        if query.campaign_year:
            filters.append(f"substr(campaign_start_date, 1, 4) = {_quote(str(query.campaign_year))}")
        if query.campaign_month:
            filters.append(f"substr(campaign_start_date, 6, 2) = {_quote(f'{query.campaign_month:02d}')}")

        sql = f"""
        SELECT campaign_id, campaign_name, country, site,
               product_id, product_name,
               campaign_start_date, campaign_end_date
        FROM dim_campaign
        WHERE {' AND '.join(filters)}
        ORDER BY campaign_start_date, campaign_id
        LIMIT 20
        """.strip()

        return [Campaign(**row) for row in self.backend.execute(sql)]
