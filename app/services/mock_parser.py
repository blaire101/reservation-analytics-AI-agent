from __future__ import annotations

import calendar
import re
from app.schemas import ExtractedRequest, ReservationQuery


_COUNTRIES = ["Germany", "France", "Singapore", "Spain", "Italy", "United Kingdom", "UK"]
_PRODUCTS = ["Xiaomi 17 Pro", "Xiaomi 17", "Xiaomi 16 Pro"]


def _detect_month(text: str) -> int | None:
    low = text.lower()
    for i in range(1, 13):
        if calendar.month_name[i].lower() in low or calendar.month_abbr[i].lower() in low:
            return i
    return None


def parse_mock_request(text: str, default_year: int = 2026) -> ExtractedRequest:
    low = text.lower().strip()

    knowledge_markers = (
        "what does",
        "what is",
        "how is",
        "how do you calculate",
        "define",
        "meaning of",
        "grain",
    )
    knowledge = any(low.startswith(x) for x in knowledge_markers)
    if "actual" in low or "how many" in low or "for cmp" in low or low.startswith("analyze"):
        knowledge = False
    if "conversion rate calculated" in low:
        knowledge = True

    metric = "campaign_summary"
    if "did not order" in low or "not ordered" in low or "reserved-but-not-ordered" in low:
        metric = "reserved_not_ordered_users"
    elif "conversion rate" in low and not knowledge:
        metric = "conversion_rate"
    elif "ordered users" in low:
        metric = "ordered_users"
    elif "how many users reserved" in low or "reserved users" in low:
        metric = "reserved_users"
    elif "user" in low and ("check" in low or "status" in low):
        metric = "user_reservation_check"

    country = next((c for c in _COUNTRIES if c.lower() in low), None)
    product = next((p for p in _PRODUCTS if p.lower() in low), None)

    campaign_id_match = re.search(r"\bCMP\d+\b", text, re.I)
    campaign_id = campaign_id_match.group(0).upper() if campaign_id_match else None

    named_campaigns = [
        "Xiaomi 17 Pro Launch",
        "Xiaomi 17 Pro Launch Campaign",
        "Back-to-School Campaign",
        "Mi Fan Campaign",
    ]
    campaign_name = next((x for x in named_campaigns if x.lower() in low), None)

    month = _detect_month(text)
    year_match = re.search(r"\b(20\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else None

    user_match = re.search(r"\b(?:user[_\s-]?id|user_id)\s*[:=]?\s*([A-Za-z0-9_-]+)", text, re.I)
    user_id = user_match.group(1) if user_match else None

    query = ReservationQuery(
        country=country,
        site=None,
        product=product,
        campaign_id=campaign_id,
        campaign_name=campaign_name,
        campaign_month=month,
        campaign_year=year,
        user_id=user_id,
    )

    return ExtractedRequest(
        intent="knowledge" if knowledge else "analytics",
        metric=metric,
        query=query,
        reasoning_summary="Offline deterministic parser used in MOCK_MODE.",
    )
