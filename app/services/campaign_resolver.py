from __future__ import annotations

from app.config import AppSettings
from app.schemas import ReservationQuery, CampaignOption
from app.services.athena import sql_literal
from app.services.query_backend import QueryBackend


class CampaignResolver:
    def __init__(self, settings: AppSettings, backend: QueryBackend):
        self.settings = settings
        self.backend = backend

    def resolve(self, q: ReservationQuery) -> list[CampaignOption]:
        s = self.settings
        filters = ["1=1"]

        if q.campaign_id:
            filters.append(f"{s.campaign_id_column} = {sql_literal(q.campaign_id)}")
        if q.campaign_name:
            filters.append(
                f"lower({s.campaign_name_column}) LIKE "
                f"lower({sql_literal('%' + q.campaign_name + '%')})"
            )
        if q.country:
            filters.append(
                "("
                f"lower({s.campaign_country_column}) = lower({sql_literal(q.country)}) "
                f"OR lower({s.campaign_site_column}) = lower({sql_literal(q.country)})"
                ")"
            )
        if q.site:
            filters.append(f"lower({s.campaign_site_column}) = lower({sql_literal(q.site)})")
        if q.product:
            filters.append(
                f"lower({s.campaign_product_name_column}) LIKE "
                f"lower({sql_literal('%' + q.product + '%')})"
            )
        if q.campaign_month:
            filters.append(f"month(date({s.campaign_start_column})) = {int(q.campaign_month)}")
        if q.campaign_year:
            filters.append(f"year(date({s.campaign_start_column})) = {int(q.campaign_year)}")
        if q.campaign_start_date:
            filters.append(
                f"date({s.campaign_end_column}) >= date({sql_literal(q.campaign_start_date)})"
            )
        if q.campaign_end_date:
            filters.append(
                f"date({s.campaign_start_column}) <= date({sql_literal(q.campaign_end_date)})"
            )

        sql = f"""
        SELECT
            {s.campaign_id_column} AS campaign_id,
            {s.campaign_name_column} AS campaign_name,
            {s.campaign_country_column} AS country,
            {s.campaign_site_column} AS site,
            {s.campaign_product_id_column} AS product_id,
            {s.campaign_product_name_column} AS product_name,
            CAST({s.campaign_start_column} AS VARCHAR) AS campaign_start_date,
            CAST({s.campaign_end_column} AS VARCHAR) AS campaign_end_date
        FROM {s.dim_database}.{s.campaign_table}
        WHERE {' AND '.join(filters)}
        ORDER BY {s.campaign_start_column}, {s.campaign_id_column}
        LIMIT 20
        """.strip()

        rows = self.backend.execute(sql, database=s.dim_database)
        return [CampaignOption(**row) for row in rows]
