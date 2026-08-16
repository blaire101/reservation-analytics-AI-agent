from __future__ import annotations

from app.analytics.sql_utils import sql_string
from app.core.models import Campaign, EntityCandidate, ReservationQuery
from app.data.backend import QueryBackend


class DimensionRepository:
    """Read governed country, product, and campaign candidates from dimensions."""

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def list_countries(self) -> list[EntityCandidate]:
        rows = self.backend.execute(
            """
            SELECT
                fcountry_code AS entity_id,
                fcountry_name AS name,
                fregion_name AS description
            FROM dim_site_df
            WHERE fis_active = 1
            ORDER BY fcountry_code
            LIMIT 100
            """.strip()
        )
        return [EntityCandidate(**row) for row in rows]

    def list_products(self) -> list[EntityCandidate]:
        rows = self.backend.execute(
            """
            SELECT
                fproduct_id AS entity_id,
                fproduct_name AS name,
                (fcategory_lv1_id || ' / ' || fcategory_lv2_id || ' / ' || fcategory_lv3_id) AS description
            FROM dim_product_df
            WHERE fis_active = 1
            ORDER BY fproduct_id
            LIMIT 100
            """.strip()
        )
        return [EntityCandidate(**row) for row in rows]

    def list_campaigns(self, query: ReservationQuery) -> list[EntityCandidate]:
        filters = ["1=1"]
        if query.country_code:
            filters.append(
                f"lower(c.fcountry_code) = lower({sql_string(query.country_code)})"
            )
        if query.product_id:
            filters.append(f"c.fproduct_id = {sql_string(query.product_id)}")
        if query.campaign_year:
            filters.append(
                f"substr(c.fstart_time, 1, 4) = {sql_string(str(query.campaign_year))}"
            )
        if query.campaign_month:
            month = f"{query.campaign_month:02d}"
            filters.append(
                f"substr(c.fstart_time, 6, 2) = {sql_string(month)}"
            )

        rows = self.backend.execute(
            f"""
            SELECT
                c.fcampaign_id AS entity_id,
                c.fcampaign_name AS name,
                (
                    c.fcampaign_type ||
                    ' | product=' || p.fproduct_name || ' (' || c.fproduct_id || ')' ||
                    ' | country=' || s.fcountry_name || ' (' || c.fcountry_code || ')' ||
                    ' | start=' || c.fstart_time
                ) AS description
            FROM dim_campaign_df c
            JOIN dim_product_df p ON c.fproduct_id = p.fproduct_id
            JOIN dim_site_df s ON c.fcountry_code = s.fcountry_code
            WHERE {' AND '.join(filters)}
            ORDER BY c.fstart_time, c.fcampaign_id
            LIMIT 100
            """.strip()
        )
        return [EntityCandidate(**row) for row in rows]

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        rows = self.backend.execute(
            f"""
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
            WHERE lower(c.fcampaign_id) = lower({sql_string(campaign_id)})
            LIMIT 1
            """.strip()
        )
        return Campaign(**rows[0]) if rows else None
