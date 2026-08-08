from __future__ import annotations

import re

from app.core.models import ExtractedRequest, ReservationQuery
from app.settings import Settings


KNOWLEDGE_HINTS = ("what is", "what does", "define", "definition", "how is", "grain")


def _metric(question: str) -> str:
    q = question.lower()
    if "conversion" in q:
        return "conversion_rate"
    if "did not order" in q or "not ordered" in q or "unconverted" in q:
        return "reserved_not_ordered"
    if "ordered" in q or "purchased" in q:
        return "ordered_users"
    if "reserved" in q:
        return "reserved_users"
    return "summary"


def _local_extract(question: str, default_year: int) -> ExtractedRequest:
    q = question.strip()
    low = q.lower()
    intent = "knowledge" if any(x in low for x in KNOWLEDGE_HINTS) else "analytics"

    campaign = re.search(r"\bCMP\d+\b", q, flags=re.I)
    month_names = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    month = next((n for name, n in month_names.items() if name in low), None)
    year_match = re.search(r"\b20\d{2}\b", q)

    country = None
    for value in ("Germany", "Singapore", "France", "Italy", "Spain"):
        if value.lower() in low:
            country = value
            break

    product = None
    product_match = re.search(r"(Phone\s+Mi\s+[A-Za-z0-9.-]+(?:\s+[A-Za-z0-9.-]+){0,2}?)(?=\s+(?:in|for|during|on)\b|[?.!,]|$)", q, flags=re.I)
    if product_match:
        product = product_match.group(1).strip()

    return ExtractedRequest(
        intent=intent,
        metric=_metric(q),
        query=ReservationQuery(
            country=country,
            product=product,
            campaign_id=campaign.group(0).upper() if campaign else None,
            campaign_month=month,
            campaign_year=int(year_match.group(0)) if year_match else (default_year if month else None),
        ),
    )


class RequestExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def extract(self, question: str) -> ExtractedRequest:
        if not self.settings.use_llm:
            return _local_extract(question, self.settings.default_year)

        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_LLM=true.")

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(ExtractedRequest)

        return self._llm.invoke(
            "Extract intent, metric, country/site, product and campaign context. "
            "Never invent missing values.\n\nQuestion: " + question
        )
