from __future__ import annotations

from app.analytics.sql_utils import sql_string
from app.core.models import Campaign
from app.data.backend import QueryBackend


class AnalyticsService:
    """Run a small allowlist of analytics metrics after context is resolved."""

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def run(
        self,
        metric: str,
        campaign: Campaign,
        detail_requested: bool = False,
    ) -> str:
        if detail_requested and metric == "reserved_not_ordered":
            return self._reserved_not_ordered_details(campaign)

        summary = self._load_summary(campaign)
        return self._format_summary(metric, campaign, summary)

    def _load_summary(self, campaign: Campaign) -> dict[str, int]:
        rows = self.backend.execute(
            f"""
            SELECT
                COUNT(DISTINCT CASE WHEN freserve_flag = 1 THEN fuser_id END) AS reserved_users,
                COUNT(DISTINCT CASE WHEN forder_flag = 1 THEN fuser_id END) AS ordered_users,
                COUNT(DISTINCT CASE WHEN ftag_reserved_not_paid = 1 THEN fuser_id END) AS reserved_not_ordered_users
            FROM dm_reservation_subject_df
            WHERE {self._context_filter(campaign)}
            """.strip()
        )
        row = rows[0] if rows else {}
        return {
            "reserved": int(row.get("reserved_users") or 0),
            "ordered": int(row.get("ordered_users") or 0),
            "not_ordered": int(row.get("reserved_not_ordered_users") or 0),
        }

    @staticmethod
    def _format_summary(
        metric: str,
        campaign: Campaign,
        summary: dict[str, int],
    ) -> str:
        reserved = summary["reserved"]
        ordered = summary["ordered"]
        not_ordered = summary["not_ordered"]
        conversion = ordered / reserved * 100.0 if reserved else 0.0
        prefix = (
            f"{campaign.campaign_id} — {campaign.campaign_name} "
            f"({campaign.country_name}): "
        )

        messages = {
            "reserved_users": f"{reserved} reserved users.",
            "ordered_users": f"{ordered} ordered users.",
            "reserved_not_ordered": f"{not_ordered} users reserved but did not order.",
            "conversion_rate": f"reservation-to-order conversion rate was {conversion:.2f}%.",
        }
        if metric in messages:
            return prefix + messages[metric]

        return (
            prefix
            + f"{reserved} reserved, {ordered} ordered, {not_ordered} not ordered, "
            + f"{conversion:.2f}% conversion."
        )

    def _reserved_not_ordered_details(self, campaign: Campaign) -> str:
        rows = self.backend.execute(
            f"""
            SELECT fuser_id_hash, fcampaign_id, fproduct_id, fcountry_code
            FROM dm_reservation_subject_df
            WHERE {self._context_filter(campaign)}
              AND ftag_reserved_not_paid = 1
            ORDER BY fuser_id_hash
            LIMIT 100
            """.strip()
        )
        hashes = ", ".join(row["fuser_id_hash"] for row in rows)
        return f"{len(rows)} detail records. fuser_id_hash: {hashes or 'none'}."

    @staticmethod
    def _context_filter(campaign: Campaign) -> str:
        return " AND ".join(
            [
                f"fcampaign_id = {sql_string(campaign.campaign_id)}",
                f"fproduct_id = {sql_string(campaign.product_id)}",
                f"fcountry_code = {sql_string(campaign.country_code)}",
            ]
        )
