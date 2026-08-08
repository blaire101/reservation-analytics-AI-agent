from __future__ import annotations

from app.core.models import Campaign, ReservationQuery
from app.data.backend import QueryBackend


def _quote(value: str) -> str:
    """
    Escape a string value for controlled SQL construction.
    """
    return "'" + value.replace("'", "''") + "'"


def missing_context(query: ReservationQuery) -> list[str]:
    """
    Check whether enough business context is available
    before resolving a campaign.

    campaign_id alone is sufficient because it uniquely
    identifies a campaign.
    """

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
    """
    Resolve natural-language business filters into matching campaigns.

    The resolver queries campaign, product, and site dimensions
    and returns zero, one, or multiple Campaign objects.

    The LangGraph workflow decides what to do with the result:

        0 matches  -> not_found
        1 match    -> continue to analytics
        2+ matches -> clarification
    """

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def resolve(self, query: ReservationQuery) -> list[Campaign]:
        """
        Find campaigns matching the supplied business context.
        """

        filters = ["1=1"]

        if query.campaign_id:
            filters.append(
                f"c.fcampaign_id = {_quote(query.campaign_id)}"
            )

        if query.country:
            filters.append(
                f"lower(s.fcountry_name) = lower({_quote(query.country)})"
            )

        if query.country_code:
            filters.append(
                f"lower(c.fcountry_code) = lower({_quote(query.country_code)})"
            )

        if query.product:
            filters.append(
                f"lower(p.fproduct_name) "
                f"LIKE lower({_quote('%' + query.product + '%')})"
            )

        if query.campaign_name:
            filters.append(
                f"lower(c.fcampaign_name) "
                f"LIKE lower({_quote('%' + query.campaign_name + '%')})"
            )

        if query.campaign_year:
            filters.append(
                f"substr(c.fstart_time, 1, 4) = "
                f"{_quote(str(query.campaign_year))}"
            )

        if query.campaign_month:
            filters.append(
                f"substr(c.fstart_time, 6, 2) = "
                f"{_quote(f'{query.campaign_month:02d}')}"
            )

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
        JOIN dim_product_df p
            ON c.fproduct_id = p.fproduct_id
        JOIN dim_site_df s
            ON c.fcountry_code = s.fcountry_code
        WHERE {' AND '.join(filters)}
        ORDER BY c.fstart_time, c.fcampaign_id
        LIMIT 20
        """.strip()

        return [
            Campaign(**row)
            for row in self.backend.execute(sql)
        ]