from __future__ import annotations

from app.analytics.sql_utils import sql_string
from app.core.models import CampaignContext
from app.data.backend import QueryBackend


class AnalyticsService:
    """Run allowlisted metrics against the trusted Data Mart."""

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def run(
        self,
        metric: str,
        context: CampaignContext,
        detail_requested: bool = False,
    ) -> str:
        if detail_requested and metric == "reserved_not_ordered":
            return self._details(context)

        summary = self._summary(context)
        return self._format(metric, context, summary)

    def _summary(self, context: CampaignContext) -> dict[str, int]:
        rows = self.backend.execute(
            f"""
            SELECT
                COUNT(DISTINCT CASE WHEN freserve_flag = 1 THEN fuser_id END) AS reserved,
                COUNT(DISTINCT CASE WHEN forder_flag = 1 THEN fuser_id END) AS ordered,
                COUNT(DISTINCT CASE WHEN ftag_reserved_not_paid = 1 THEN fuser_id END) AS not_ordered
            FROM dm_reservation_subject_df
            WHERE {self._where(context)}
            """.strip()
        )
        row = rows[0] if rows else {}
        return {k: int(row.get(k) or 0) for k in ("reserved", "ordered", "not_ordered")}

    def _details(self, context: CampaignContext) -> str:
        rows = self.backend.execute(
            f"""
            SELECT fuser_id_hash, fcampaign_id, fproduct_id, fcountry_code
            FROM dm_reservation_subject_df
            WHERE {self._where(context)}
              AND ftag_reserved_not_paid = 1
            ORDER BY fuser_id_hash
            LIMIT 100
            """.strip()
        )
        hashes = ", ".join(row["fuser_id_hash"] for row in rows)
        return f"{len(rows)} detail records. fuser_id_hash: {hashes or 'none'}."

    @staticmethod
    def _where(context: CampaignContext) -> str:
        filters = [
            f"fcampaign_id = {sql_string(context.campaign_id)}",
            f"fcountry_code = {sql_string(context.country_code)}",
        ]
        if context.product_id:
            filters.append(f"fproduct_id = {sql_string(context.product_id)}")
        return " AND ".join(filters)

    @staticmethod
    def _format(
        metric: str,
        context: CampaignContext,
        summary: dict[str, int],
    ) -> str:
        reserved = summary["reserved"]
        ordered = summary["ordered"]
        not_ordered = summary["not_ordered"]
        conversion = ordered / reserved * 100 if reserved else 0

        scope = f"{context.campaign_id} — {context.campaign_name} ({context.country_name})"
        if context.product_name:
            scope += f", {context.product_name}"

        messages = {
            "reserved_users": f"{reserved} reserved users.",
            "ordered_users": f"{ordered} ordered users.",
            "reserved_not_ordered": f"{not_ordered} users reserved but did not order.",
            "conversion_rate": f"reservation-to-order conversion rate was {conversion:.2f}%.",
        }
        if metric in messages:
            return f"{scope}: {messages[metric]}"

        return (
            f"{scope}: {reserved} reserved, {ordered} ordered, "
            f"{not_ordered} not ordered, {conversion:.2f}% conversion."
        )
