from __future__ import annotations

import re

from app.core.models import ExtractedRequest, ReservationQuery
from app.settings import Settings


KNOWLEDGE_HINTS = (
    "what is",
    "what does",
    "mean",
    "define",
    "definition",
    "how is",
    "grain",
    "field",
    "table",
    "是什么",
    "什么意思",
    "定义",
    "口径",
    "字段",
    "表结构",
    "粒度",
)
DETAIL_HINTS = (
    "show users",
    "list users",
    "details",
    "which users",
    "用户明细",
    "用户列表",
    "哪些用户",
)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _contains(question: str, hints: tuple[str, ...]) -> bool:
    low = question.lower()
    return any(
        hint.lower() in low if hint.isascii() else hint in question
        for hint in hints
    )


def _detect_metric(question: str) -> str:
    low = question.lower()
    if "conversion" in low or "转化率" in question:
        return "conversion_rate"
    if any(term in low for term in ("did not order", "not ordered", "unconverted")):
        return "reserved_not_ordered"
    if "预约未下单" in question:
        return "reserved_not_ordered"
    if "ordered" in low or "purchased" in low or "下单用户" in question:
        return "ordered_users"
    if "reserved" in low or "reservation" in low or "预约" in question:
        return "reserved_users"
    return "summary"


def _extract_offline_query(question: str, default_year: int) -> ReservationQuery:
    """Parse just enough bundled sample wording for local tests and demos."""

    query = ReservationQuery()
    low = question.lower()

    campaign_id = re.search(r"\b(CMP\d+)\b", question, flags=re.I)
    if campaign_id:
        query.campaign_id = campaign_id.group(1).upper()

    if re.search(r"\bGermany\b", question, flags=re.I):
        query.country = "Germany"
    elif re.search(r"\bSingapore\b", question, flags=re.I):
        query.country = "Singapore"

    product_patterns = (
        r"Phone\s+Mi\s+17\s+Pro",
        r"Mi\s+17\s+Pro",
        r"Phone\s+Mi\s+17",
        r"Mi\s+17",
    )
    for pattern in product_patterns:
        match = re.search(pattern, question, flags=re.I)
        if match:
            query.product = re.sub(r"\s+", " ", match.group(0)).strip()
            break

    for month_name, month_number in MONTHS.items():
        if month_name in low:
            query.campaign_month = month_number
            break

    year = re.search(r"\b(20\d{2})\b", question)
    if year:
        query.campaign_year = int(year.group(1))
    elif query.campaign_month:
        query.campaign_year = default_year

    return query


def _offline_extract(question: str, default_year: int) -> ExtractedRequest:
    if _contains(question, KNOWLEDGE_HINTS):
        return ExtractedRequest(intent="knowledge")

    return ExtractedRequest(
        intent="analytics",
        metric=_detect_metric(question),
        detail_requested=_contains(question, DETAIL_HINTS),
        query=_extract_offline_query(question, default_year),
    )


class RequestExtractor:
    """Convert one user question into a typed request; do not resolve warehouse IDs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def extract(self, question: str) -> ExtractedRequest:
        if not self.settings.use_llm:
            return _offline_extract(question, self.settings.default_year)
        return self._extract_with_llm(question)

    def _extract_with_llm(self, question: str) -> ExtractedRequest:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_ENABLED=true.")

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(ExtractedRequest)

        prompt = f"""Extract a typed request for a Reservation Analytics AI Agent.
The user may write in English, Chinese, or mixed language.

Intent:
- knowledge = definitions, metric rules, metadata, grain, fields, or tables
- analytics = actual counts, rates, lists, performance, or campaign results

Entity rules:
- Keep country, product, and campaign wording as the user expressed it.
- Do not translate free text into warehouse IDs.
- Set country_code, product_id, or campaign_id only when the user explicitly supplied that code/ID.
- Never invent missing values. A later resolver will query governed dimensions.

Question: {question}
"""
        result = self._llm.invoke(prompt)
        self._remove_invented_ids(result, question)
        return result

    @staticmethod
    def _remove_invented_ids(result: ExtractedRequest, question: str) -> None:
        raw = question.lower()
        query = result.query

        if query.campaign_id and query.campaign_id.lower() not in raw:
            query.campaign_id = None
        if query.product_id and query.product_id.lower() not in raw:
            query.product_id = None
        if query.country_code and not re.search(
            rf"\b{re.escape(query.country_code.lower())}\b",
            raw,
        ):
            query.country_code = None
