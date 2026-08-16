from __future__ import annotations

import re

from app.core.models import ExtractedRequest, ReservationQuery
from app.settings import Settings


KNOWLEDGE_WORDS = (
    "what is", "what does", "mean", "define", "definition",
    "how is", "grain", "field", "table",
    "是什么", "什么意思", "定义", "口径", "字段", "表结构", "粒度",
)
DETAIL_WORDS = (
    "show users", "list users", "details", "which users",
    "用户明细", "用户列表", "哪些用户",
)
MONTHS = {
    name: number
    for number, name in enumerate(
        (
            "january", "february", "march", "april", "may", "june",
            "july", "august", "september", "october", "november", "december",
        ),
        start=1,
    )
}


def contains_any(text: str, words: tuple[str, ...]) -> bool:
    low = text.lower()
    return any(word.lower() in low if word.isascii() else word in text for word in words)


def detect_metric(question: str) -> str:
    low = question.lower()
    if "conversion" in low or "转化率" in question:
        return "conversion_rate"
    if (
        "did not order" in low
        or "not ordered" in low
        or "unconverted" in low
        or "预约未下单" in question
    ):
        return "reserved_not_ordered"
    if "ordered" in low or "purchased" in low or "下单用户" in question:
        return "ordered_users"
    if "reserved" in low or "reservation" in low or "预约" in question:
        return "reserved_users"
    return "summary"


def parse_local_query(question: str, default_year: int) -> ReservationQuery:
    """Small deterministic parser used by local tests and offline demos."""

    query = ReservationQuery()
    low = question.lower()

    campaign_id = re.search(r"\b(CMP\d+)\b", question, flags=re.I)
    if campaign_id:
        query.campaign_id = campaign_id.group(1).upper()

    for country in ("Germany", "Singapore"):
        if re.search(rf"\b{country}\b", question, flags=re.I):
            query.country = country
            break

    # Longest product pattern first so "Mi 17 Pro" is not truncated to "Mi 17".
    for pattern in (
        r"Phone\s+Mi\s+17\s+Pro",
        r"Mi\s+17\s+Pro",
        r"Phone\s+Mi\s+17",
        r"Mi\s+17",
    ):
        match = re.search(pattern, question, flags=re.I)
        if match:
            query.product = re.sub(r"\s+", " ", match.group(0)).strip()
            break

    for month, number in MONTHS.items():
        if month in low:
            query.campaign_month = number
            break

    year = re.search(r"\b(20\d{2})\b", question)
    if year:
        query.campaign_year = int(year.group(1))
    elif query.campaign_month:
        query.campaign_year = default_year

    return query


class RequestExtractor:
    """Turn a user question into a typed request; never invent warehouse IDs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def extract(self, question: str) -> ExtractedRequest:
        if self.settings.use_llm:
            return self._extract_with_llm(question)

        if contains_any(question, KNOWLEDGE_WORDS):
            return ExtractedRequest(intent="knowledge")

        return ExtractedRequest(
            intent="analytics",
            metric=detect_metric(question),
            detail_requested=contains_any(question, DETAIL_WORDS),
            query=parse_local_query(question, self.settings.default_year),
        )

    def _extract_with_llm(self, question: str) -> ExtractedRequest:
        if not self.settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_ENABLED=true."
            )

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(ExtractedRequest)

        prompt = f"""Extract a typed request for a Reservation Analytics AI Agent.

Intent:
- knowledge: definitions, metric rules, metadata, grain, fields, tables
- analytics: counts, rates, user lists, campaign results

Entity rules:
- Keep country, product, and campaign wording as the user wrote it.
- Set an ID/code only when the user explicitly supplied it.
- Never invent missing IDs; the resolver will use governed dimensions.

Question: {question}
"""
        result = self._llm.invoke(prompt)
        self._remove_invented_ids(result, question)
        return result

    @staticmethod
    def _remove_invented_ids(
        result: ExtractedRequest,
        question: str,
    ) -> None:
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
