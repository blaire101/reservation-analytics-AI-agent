from __future__ import annotations

from app.analytics.sql_utils import sql_string
from app.core.models import (
    CampaignContext,
    EntityCandidate,
    ReservationQuery,
)
from app.data.backend import QueryBackend


class DimensionRepository:
    """
    Read governed business data from dimension tables.

    This class does NOT decide which entity is correct.

    It only returns:
        - country candidates
        - product candidates
        - campaign candidates
        - final CampaignContext
    """

    def __init__(
        self,
        backend: QueryBackend,
    ):
        self.backend = backend

    def list_countries(
        self,
    ) -> list[EntityCandidate]:
        """Return active country candidates from dim_site_df."""

        rows = self.backend.execute(
            """
            SELECT
                fcountry_code AS entity_id,
                fcountry_name AS name,
                fregion_name AS description
            FROM dim_site_df
            WHERE fis_active = 1
            ORDER BY fcountry_code
            """.strip()
        )

        return [
            EntityCandidate(**row)
            for row in rows
        ]

    def list_products(
        self,
    ) -> list[EntityCandidate]:
        """Return active product candidates from dim_product_df."""

        rows = self.backend.execute(
            """
            SELECT
                fproduct_id AS entity_id,
                fproduct_name AS name,
                fcategory_lv1_id AS description
            FROM dim_product_df
            WHERE fis_active = 1
            ORDER BY fproduct_id
            """.strip()
        )

        return [
            EntityCandidate(**row)
            for row in rows
        ]

    def list_campaigns(
        self,
        query: ReservationQuery,
    ) -> list[EntityCandidate]:
        """
        Return campaign candidates.

        Use already-resolved context to reduce the candidate set:
            country
            product, if supplied
            year
            month
        """

        filters = ["1=1"]

        # Country filter
        if query.country_code:
            filters.append(
                "lower(c.fcountry_code) = lower("
                f"{sql_string(query.country_code)})"
            )

        # Product is optional.
        if query.product_id:
            filters.append(
                f"c.fproduct_id = {sql_string(query.product_id)}"
            )

        # Optional time filters
        # Default time window
        if not query.campaign_year and not query.campaign_month:
            cutoff_year = date.today().year - 2
            filters.append(
                f"substr(c.fstart_time, 1, 4) >= '{cutoff_year}'"
            )

        # User-specified year
        if query.campaign_year:
            filters.append(
                "substr(c.fstart_time, 1, 4) = "
                f"{sql_string(str(query.campaign_year))}"
            )

        # User-specified month
        if query.campaign_month:
            month = f"{query.campaign_month:02d}"

            filters.append(
                "substr(c.fstart_time, 6, 2) = "
                f"{sql_string(month)}"
            )

        sql = f"""
            SELECT DISTINCT
                c.fcampaign_id AS entity_id,
                c.fcampaign_name AS name,
                (
                    c.fcampaign_type ||
                    ' | country=' || s.fcountry_name ||
                    ' | start=' || c.fstart_time
                ) AS description
            FROM dim_campaign_df c
            JOIN dim_site_df s
              ON c.fcountry_code = s.fcountry_code
            WHERE {' AND '.join(filters)}
            ORDER BY c.fcampaign_id
        """.strip()

        rows = self.backend.execute(sql)

        return [
            EntityCandidate(**row)
            for row in rows
        ]

    def get_context(
            self,
            campaign_id: str,
            country_code: str | None,
            product_id: str | None,
    ) -> CampaignContext | None:
        """
        Build the final CampaignContext.

        Rules:
        - Campaign is the main entity and must already be resolved.
        - Country is optional.
        - Product is optional.
        - If country/product is not supplied, do not force a filter.
        """

        # Always identify the campaign.
        filters = [
            "lower(c.fcampaign_id) = lower("
            f"{sql_string(campaign_id)})"
        ]

        # Optional country filter.
        if country_code:
            filters.append(
                "lower(c.fcountry_code) = lower("
                f"{sql_string(country_code)})"
            )

        # Optional product filter.
        if product_id:
            filters.append(
                f"c.fproduct_id = {sql_string(product_id)}"
            )

        sql = f"""
            SELECT DISTINCT
                c.fcampaign_id AS campaign_id,
                c.fcampaign_name AS campaign_name
            FROM dim_campaign_df c
            WHERE {' AND '.join(filters)}
            LIMIT 2
        """.strip()

        rows = self.backend.execute(sql)

        # Campaign/filter combination must exist.
        if not rows:
            return None

        # Campaign ID is already the stable main entity.
        context = CampaignContext(
            campaign_id=rows[0]["campaign_id"],
            campaign_name=rows[0]["campaign_name"],
        )

        # Add country metadata only when country was supplied.
        if country_code:
            country_rows = self.backend.execute(
                f"""
                SELECT
                    fcountry_code AS country_code,
                    fcountry_name AS country_name
                FROM dim_site_df
                WHERE lower(fcountry_code) = lower(
                    {sql_string(country_code)}
                )
                LIMIT 1
                """.strip()
            )

            if country_rows:
                context.country_code = country_rows[0]["country_code"]
                context.country_name = country_rows[0]["country_name"]

        # Add product metadata only when product was supplied.
        if product_id:
            product_rows = self.backend.execute(
                f"""
                SELECT
                    fproduct_id AS product_id,
                    fproduct_name AS product_name
                FROM dim_product_df
                WHERE fproduct_id = {sql_string(product_id)}
                LIMIT 1
                """.strip()
            )

            if product_rows:
                context.product_id = product_rows[0]["product_id"]
                context.product_name = product_rows[0]["product_name"]

        return context
