from __future__ import annotations

from app.core.models import ExtractedRequest, ReservationQuery
from app.settings import Settings

KNOWLEDGE_HINTS = ("what is", "what does", "define", "definition", "how is", "grain", "field", "table")
DETAIL_HINTS = ("show", "list", "detail", "which users", "user list")


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


def _local_extract(question: str) -> ExtractedRequest:
    """Minimal fallback used when LLM mode is disabled."""

    text = question.lower()

    if "what does" in text or "mean" in text:
        return ExtractedRequest(intent="knowledge")

    return ExtractedRequest(
        intent="analytics",
        metric="summary",
        query=ReservationQuery(),
    )


def _local_extract(self, question: str) -> ExtractedRequest:
    """
    Minimal fallback when LLM mode is disabled.

    Only detects:
    - knowledge vs analytics
    - requested metric
    - whether detail rows are requested

    It does not extract campaign/product/country.

    question example:
        knowledge: 1. What does reserved but not ordered mean?
        analytics: 2. How many users reserved?
    """

    text = question.lower()

    # Knowledge question.
    if any(word in text for word in ["what is", "what does", "mean", "definition"]):
        return ExtractedRequest(
            intent="knowledge",
        )

    # Analytics question.
    metric = "summary"

    if "conversion" in text:
        metric = "conversion_rate"
    elif "not ordered" in text or "reserved but not ordered" in text:
        metric = "reserved_not_ordered"
    elif "ordered" in text:
        metric = "ordered_users"
    elif "reserved" in text or "reservation" in text:
        metric = "reserved_users"

    detail_requested = any(
        word in text
        for word in ["show users", "list users", "details"]
    )

    return ExtractedRequest(
        intent="analytics",
        metric=metric,
        detail_requested=detail_requested,
        query=ReservationQuery(),
    )


"""
User Question
   ↓
RequestExtractor
   ↓
ExtractedRequest  ( Pydantic Data Model )
"""

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

        return self._llm.invoke(
            "Extract intent, metric, detail request, country, product and campaign context. "
            "Never invent missing values.\n\nQuestion: " + question
        )
