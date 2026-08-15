from __future__ import annotations

import re

from app.core.models import ExtractedRequest, ReservationQuery
from app.settings import Settings


KNOWLEDGE_HINTS = (
    "what is", "what does", "mean", "define", "definition", "how is", "grain", "field", "table",
    "是什么", "什么意思", "定义", "口径", "字段", "表结构", "粒度",
)
DETAIL_HINTS = ("show users", "list users", "details", "which users", "用户明细", "用户列表", "哪些用户")


def _metric(question: str) -> str:
    q = question.lower()
    if "conversion" in q or "转化率" in question:
        return "conversion_rate"
    if any(x in q for x in ("did not order", "not ordered", "unconverted")) or "预约未下单" in question:
        return "reserved_not_ordered"
    if "ordered" in q or "purchased" in q or "下单用户" in question:
        return "ordered_users"
    if "reserved" in q or "reservation" in q or "预约" in question:
        return "reserved_users"
    return "summary"


def _local_extract(question: str, default_year: int = 2026) -> ExtractedRequest:
    """Deterministic fallback for local tests. LLM mode handles broader multilingual phrasing."""

    low = question.lower()
    if any(hint in low for hint in KNOWLEDGE_HINTS if hint.isascii()) or any(
        hint in question for hint in KNOWLEDGE_HINTS if not hint.isascii()
    ):
        return ExtractedRequest(intent="knowledge")

    query = ReservationQuery()

    campaign = re.search(r"\b(CMP\d+)\b", question, flags=re.I)
    if campaign:
        query.campaign_id = campaign.group(1).upper()

    # Small deterministic parser only for the bundled sample data / offline tests.
    if re.search(r"\bGermany\b", question, flags=re.I):
        query.country = "Germany"
    elif re.search(r"\bSingapore\b", question, flags=re.I):
        query.country = "Singapore"

    product_patterns = [
        r"Phone\s+Mi\s+17\s+Pro", r"Mi\s+17\s+Pro",
        r"Phone\s+Mi\s+17", r"Mi\s+17",
    ]
    for pattern in product_patterns:
        match = re.search(pattern, question, flags=re.I)
        if match:
            query.product = re.sub(r"\s+", " ", match.group(0)).strip()
            break

    month_names = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    for name, month in month_names.items():
        if name in low:
            query.campaign_month = month
            break
    year = re.search(r"\b(20\d{2})\b", question)
    if year:
        query.campaign_year = int(year.group(1))
    elif query.campaign_month:
        query.campaign_year = default_year

    detail_requested = any(h in low for h in DETAIL_HINTS if h.isascii()) or any(
        h in question for h in DETAIL_HINTS if not h.isascii()
    )

    return ExtractedRequest(
        intent="analytics",
        metric=_metric(question),
        detail_requested=detail_requested,
        query=query,
    )


class RequestExtractor:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def extract(self, question: str) -> ExtractedRequest:
        if not self.settings.use_llm:
            return _local_extract(question, self.settings.default_year)
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_ENABLED=true.")

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(ExtractedRequest)

        prompt = """You extract typed business context for a Reservation Analytics AI Agent.
The user may write in English, Chinese, or mixed language.

Intent rules:
- knowledge: asks for definitions, meanings, metric rules, metadata, grain, fields, tables, or how something is defined.
- analytics: asks for actual counts, rates, lists, performance, campaign results, or detail records.

Entity rules:
- Extract country, product, campaign name/month/year as the user expressed them. They may be informal or multilingual.
- Do NOT translate free-text entities into warehouse IDs yourself.
- Set country_code, product_id, or campaign_id only when the user explicitly supplied that code/ID.
- Never invent missing values. The application will resolve free text against governed dimensions and ask for clarification if ambiguous.

Question: """ + question
        result = self._llm.invoke(prompt)

        # Defense in depth: stable warehouse IDs are accepted from extraction
        # only when the user literally supplied them. Otherwise the resolver
        # must obtain IDs from governed dimensions.
        raw = question.lower()
        if result.query.campaign_id and result.query.campaign_id.lower() not in raw:
            result.query.campaign_id = None
        if result.query.product_id and result.query.product_id.lower() not in raw:
            result.query.product_id = None
        if result.query.country_code and not re.search(
            rf"\b{re.escape(result.query.country_code.lower())}\b", raw
        ):
            result.query.country_code = None
        return result
