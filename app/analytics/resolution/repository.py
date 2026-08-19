"""Read governed country, product, and campaign data from dimension tables.

This module contains deterministic SQL lookups only. There is no LLM logic.
The resolvers call this repository to validate explicit IDs and to retrieve
candidate entities for natural-language names.
"""

from __future__ import annotations

from app.analytics.models.context import CampaignContext, EntityCandidate
from app.analytics.models.request import ReservationQuery
from app.analytics.query.backend import QueryBackend
from app.analytics.query.sql_utils import sql_string


class DimensionRepository:
    """Provide small governed dimension-table queries for entity resolution."""

    def __init__(self, backend: QueryBackend):
        """Store the query backend used to execute deterministic lookup SQL."""
        self.backend = backend

    def country_by_code(self, code: str) -> EntityCandidate | None:
        """Validate one explicit country code by exact case-insensitive match."""
        sql = f"""
            SELECT
                fcountry_code AS entity_id,
                fcountry_name AS name,
                fregion_name AS description
            FROM dim_site_df
            WHERE fis_active = 1
              AND lower(fcountry_code) = lower({sql_string(code)})
            LIMIT 1
        """.strip()

        rows = self.backend.execute(sql)
        return EntityCandidate(**rows[0]) if rows else None

    def countries_by_name(self, name: str) -> list[EntityCandidate]:
        """Find governed country candidates from a natural-language name."""
        sql = f"""
            SELECT
                fcountry_code AS entity_id,
                fcountry_name AS name,
                fregion_name AS description
            FROM dim_site_df
            WHERE fis_active = 1
              AND lower(fcountry_name) LIKE lower({sql_string('%' + name + '%')})
            ORDER BY fcountry_code
        """.strip()

        rows = self.backend.execute(sql)
        return [EntityCandidate(**row) for row in rows]

    def product_by_id(self, product_id: str) -> EntityCandidate | None:
        """Validate one explicit product ID by exact case-insensitive match."""
        sql = f"""
            SELECT
                fproduct_id AS entity_id,
                fproduct_name AS name,
                fcategory_lv1_id AS description
            FROM dim_product_df
            WHERE fis_active = 1
              AND lower(fproduct_id) = lower({sql_string(product_id)})
            LIMIT 1
        """.strip()

        rows = self.backend.execute(sql)
        return EntityCandidate(**rows[0]) if rows else None

    def products_by_name(self, name: str) -> list[EntityCandidate]:
        """Find governed product candidates from a natural-language name."""
        sql = f"""
            SELECT
                fproduct_id AS entity_id,
                fproduct_name AS name,
                fcategory_lv1_id AS description
            FROM dim_product_df
            WHERE fis_active = 1
              AND lower(fproduct_name) LIKE lower({sql_string('%' + name + '%')})
            ORDER BY fproduct_id
        """.strip()

        rows = self.backend.execute(sql)
        return [EntityCandidate(**row) for row in rows]

    def campaign_context_by_id(
        self,
        campaign_id: str,
        country_code: str | None = None,
        product_id: str | None = None,
    ) -> CampaignContext | None:
        """Validate a campaign ID and build the stable context used by SQL.

        Args:
            campaign_id: Explicit or resolved stable campaign ID.
            country_code: Optional stable country code used to narrow the match.
            product_id: Optional stable product ID used to narrow the match.

        Returns:
            Exactly one ``CampaignContext`` or ``None`` when zero/multiple
            contexts match.
        """
        filters = [
            f'lower(c.fcampaign_id) = lower({sql_string(campaign_id)})'
        ]

        # Already-resolved IDs make the campaign validation more precise.
        if country_code:
            filters.append(
                f'lower(c.fcountry_code) = lower({sql_string(country_code)})'
            )
        if product_id:
            filters.append(f'c.fproduct_id = {sql_string(product_id)}')

        sql = f"""
            SELECT DISTINCT
                c.fcampaign_id AS campaign_id,
                c.fcampaign_name AS campaign_name,
                c.fcountry_code AS country_code,
                s.fcountry_name AS country_name
            FROM dim_campaign_df c
            JOIN dim_site_df s
              ON c.fcountry_code = s.fcountry_code
            WHERE {' AND '.join(filters)}
            LIMIT 2
        """.strip()

        rows = self.backend.execute(sql)

        # Exactly one governed context is required before analytics can run.
        if len(rows) != 1:
            return None

        context = CampaignContext(**rows[0])

        # Attach friendly product information when the query is product-scoped.
        if product_id:
            product = self.product_by_id(product_id)
            if product:
                context.product_id = product.entity_id
                context.product_name = product.name

        return context

    def campaigns_by_context(self, query: ReservationQuery) -> list[EntityCandidate]:
        """Search campaign candidates using the available structured context.

        Possible filters:
            country_code, product_id, campaign_name, campaign_year,
            campaign_month.
        """
        # Start with a neutral condition so optional filters can be appended.
        filters = ['1=1']

        if query.country_code:
            filters.append(
                f'lower(c.fcountry_code) = lower({sql_string(query.country_code)})'
            )
        if query.product_id:
            filters.append(f'c.fproduct_id = {sql_string(query.product_id)}')
        if query.campaign_name:
            filters.append(
                'lower(c.fcampaign_name) LIKE lower('
                + sql_string('%' + query.campaign_name + '%')
                + ')'
            )
        if query.campaign_year:
            filters.append(
                f'substr(c.fstart_time, 1, 4) = {sql_string(str(query.campaign_year))}'
            )
        if query.campaign_month:
            month = f'{query.campaign_month:02d}'
            filters.append(
                f'substr(c.fstart_time, 6, 2) = {sql_string(month)}'
            )

        sql = f"""
            SELECT DISTINCT
                c.fcampaign_id AS entity_id,
                c.fcampaign_name AS name,
                c.fcampaign_type ||
                    ' | country=' || s.fcountry_name ||
                    ' | start=' || c.fstart_time AS description
            FROM dim_campaign_df c
            JOIN dim_site_df s
              ON c.fcountry_code = s.fcountry_code
            WHERE {' AND '.join(filters)}
            ORDER BY c.fcampaign_id
        """.strip()

        rows = self.backend.execute(sql)
        return [EntityCandidate(**row) for row in rows]
