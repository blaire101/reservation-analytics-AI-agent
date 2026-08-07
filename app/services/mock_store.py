from __future__ import annotations

import csv
from app.config import AppSettings
from app.schemas import CampaignOption, AnalyticsResult


class MockStore:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        with settings.mock_campaign_file.open(newline="", encoding="utf-8") as f:
            self.campaigns = list(csv.DictReader(f))
        with settings.mock_dm_file.open(newline="", encoding="utf-8") as f:
            self.dm_rows = list(csv.DictReader(f))

    def find_campaigns(
        self,
        *,
        campaign_id: str | None,
        campaign_name: str | None,
        country: str | None,
        product: str | None,
        month: int | None,
        year: int | None,
    ) -> list[CampaignOption]:
        rows = self.campaigns

        def keep(row: dict) -> bool:
            if campaign_id and row["campaign_id"].lower() != campaign_id.lower():
                return False
            if campaign_name and campaign_name.lower() not in row["campaign_name"].lower():
                return False
            if country and country.lower() not in {
                row["country"].lower(),
                row["site"].lower(),
            }:
                return False
            if product and product.lower() not in row["product_name"].lower():
                return False
            if month and int(row["campaign_start_date"][5:7]) != month:
                return False
            if year and int(row["campaign_start_date"][:4]) != year:
                return False
            return True

        return [CampaignOption(**r) for r in rows if keep(r)]

    def analytics(self, campaign_id: str, user_id: str | None = None) -> AnalyticsResult:
        rows = [r for r in self.dm_rows if r["campaign_id"] == campaign_id]

        if user_id:
            user_rows = [r for r in rows if r["user_id"] == user_id]
            return AnalyticsResult(
                campaign_id=campaign_id,
                user_rows=user_rows,
            )

        reserved = {
            r["user_id"] for r in rows if int(r["reserve_flag"]) == 1
        }
        ordered = {
            r["user_id"] for r in rows if int(r["order_flag"]) == 1
        }
        rno = {
            r["user_id"] for r in rows if int(r["tag_reserved_not_paid"]) == 1
        }
        conversion = (len(ordered) / len(reserved)) if reserved else 0.0

        return AnalyticsResult(
            campaign_id=campaign_id,
            reserved_users=len(reserved),
            ordered_users=len(ordered),
            reserved_not_ordered_users=len(rno),
            conversion_rate=conversion,
        )
