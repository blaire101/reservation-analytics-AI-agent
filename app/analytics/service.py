from __future__ import annotations

from app.core.models import Campaign
from app.data.backend import QueryBackend


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class AnalyticsService:
    """Executes allowlisted metric SQL after campaign resolution."""

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def run(self, metric: str, campaign: Campaign) -> str:
        sql = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN reserve_flag = 1 THEN user_id END) AS reserved_users,
            COUNT(DISTINCT CASE WHEN order_flag = 1 THEN user_id END) AS ordered_users,
            COUNT(DISTINCT CASE WHEN reserved_not_ordered_flag = 1 THEN user_id END) AS reserved_not_ordered_users
        FROM dm_reservation_conversion
        WHERE campaign_id = {_quote(campaign.campaign_id)}
        """.strip()

        row = self.backend.execute(sql)[0]
        reserved = int(row["reserved_users"] or 0)
        ordered = int(row["ordered_users"] or 0)
        unconverted = int(row["reserved_not_ordered_users"] or 0)
        conversion = (ordered / reserved * 100.0) if reserved else 0.0

        prefix = f"{campaign.campaign_id} — {campaign.campaign_name}: "
        if metric == "reserved_users":
            return prefix + f"{reserved} reserved users."
        if metric == "ordered_users":
            return prefix + f"{ordered} ordered users."
        if metric == "reserved_not_ordered":
            return prefix + f"{unconverted} users reserved but did not order."
        if metric == "conversion_rate":
            return prefix + f"reservation-to-order conversion rate was {conversion:.2f}%."

        return (
            prefix
            + f"{reserved} reserved users, {ordered} ordered users, "
            + f"{unconverted} reserved-but-not-ordered users, and {conversion:.2f}% conversion."
        )
