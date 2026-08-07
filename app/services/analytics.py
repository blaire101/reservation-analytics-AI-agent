from __future__ import annotations

from app.config import AppSettings
from app.schemas import AnalyticsResult
from app.services.athena import sql_literal
from app.services.query_backend import QueryBackend


class AnalyticsService:
    def __init__(self, settings: AppSettings, backend: QueryBackend):
        self.settings = settings
        self.backend = backend

    def query(self, campaign_id: str, user_id: str | None = None) -> AnalyticsResult:
        s = self.settings

        if user_id:
            sql = f"""
            SELECT
                user_id,
                campaign_id,
                product_id,
                site,
                CAST(reserve_time AS VARCHAR) AS reserve_time,
                reserve_flag,
                order_flag,
                tag_reserved_not_paid,
                order_id,
                CAST(order_time AS VARCHAR) AS order_time
            FROM {s.dm_database}.{s.dm_table}
            WHERE campaign_id = {sql_literal(campaign_id)}
              AND user_id = {sql_literal(user_id)}
            LIMIT 100
            """.strip()
            rows = self.backend.execute(sql, database=s.dm_database)
            return AnalyticsResult(campaign_id=campaign_id, user_rows=rows)

        # The LLM never writes this SQL. The application uses a fixed,
        # allowlisted template after campaign resolution returns one ID.
        sql = f"""
        WITH agg AS (
            SELECT
                COUNT(DISTINCT CASE WHEN reserve_flag = 1 THEN user_id END) AS reserved_users,
                COUNT(DISTINCT CASE WHEN order_flag = 1 THEN user_id END) AS ordered_users,
                COUNT(DISTINCT CASE WHEN tag_reserved_not_paid = 1 THEN user_id END) AS reserved_not_ordered_users
            FROM {s.dm_database}.{s.dm_table}
            WHERE campaign_id = {sql_literal(campaign_id)}
        )
        SELECT
            reserved_users,
            ordered_users,
            reserved_not_ordered_users,
            CASE
                WHEN reserved_users = 0 THEN 0.0
                ELSE CAST(ordered_users AS DOUBLE) / CAST(reserved_users AS DOUBLE)
            END AS conversion_rate
        FROM agg
        """.strip()

        rows = self.backend.execute(sql, database=s.dm_database)
        if not rows:
            return AnalyticsResult(campaign_id=campaign_id)

        row = rows[0]
        return AnalyticsResult(
            campaign_id=campaign_id,
            reserved_users=int(row.get("reserved_users") or 0),
            ordered_users=int(row.get("ordered_users") or 0),
            reserved_not_ordered_users=int(row.get("reserved_not_ordered_users") or 0),
            conversion_rate=float(row.get("conversion_rate") or 0.0),
        )
