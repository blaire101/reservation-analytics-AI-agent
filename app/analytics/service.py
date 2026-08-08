from __future__ import annotations

from app.core.models import Campaign
from app.data.backend import QueryBackend


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class AnalyticsService:
    """Executes controlled aggregate or detail SQL after context resolution."""

    def __init__(self, backend: QueryBackend):
        self.backend = backend

    def _where(self, campaign: Campaign) -> str:
        return " AND ".join([
            f"fcampaign_id = {_quote(campaign.campaign_id)}",
            f"fproduct_id = {_quote(campaign.product_id)}",
            f"fcountry_code = {_quote(campaign.country_code)}",
        ])

    def run(self, metric: str, campaign: Campaign, detail_requested: bool = False) -> str:
        if detail_requested and metric == "reserved_not_ordered":
            return self._detail(campaign)

        sql = f"""
        SELECT
            COUNT(DISTINCT CASE WHEN freserve_flag = 1 THEN fuser_id END) AS reserved_users,
            COUNT(DISTINCT CASE WHEN forder_flag = 1 THEN fuser_id END) AS ordered_users,
            COUNT(DISTINCT CASE WHEN ftag_reserved_not_paid = 1 THEN fuser_id END) AS reserved_not_ordered_users
        FROM dm_reservation_subject_df
        WHERE {self._where(campaign)}
        """.strip()
        row = self.backend.execute(sql)[0]
        reserved = int(row["reserved_users"] or 0)
        ordered = int(row["ordered_users"] or 0)
        unconverted = int(row["reserved_not_ordered_users"] or 0)
        conversion = ordered / reserved * 100.0 if reserved else 0.0

        prefix = f"{campaign.campaign_id} — {campaign.campaign_name} ({campaign.country_name}): "
        if metric == "reserved_users":
            return prefix + f"{reserved} reserved users."
        if metric == "ordered_users":
            return prefix + f"{ordered} ordered users."
        if metric == "reserved_not_ordered":
            return prefix + f"{unconverted} users reserved but did not order."
        if metric == "conversion_rate":
            return prefix + f"reservation-to-order conversion rate was {conversion:.2f}%."
        return prefix + f"{reserved} reserved, {ordered} ordered, {unconverted} not ordered, {conversion:.2f}% conversion."

    def _detail(self, campaign: Campaign) -> str:
        sql = f"""
        SELECT fuser_id_hash, fcampaign_id, fproduct_id, fcountry_code
        FROM dm_reservation_subject_df
        WHERE {self._where(campaign)}
          AND ftag_reserved_not_paid = 1
        ORDER BY fuser_id_hash
        LIMIT 100
        """.strip()
        rows = self.backend.execute(sql)
        hashes = ", ".join(row["fuser_id_hash"] for row in rows)
        return f"{len(rows)} detail records. fuser_id_hash: {hashes or 'none'}."
