from __future__ import annotations

from app.core.models import ExtractedRequest
from app.settings import Settings


def _build_llm(settings: Settings):
    """Create the structured LLM used for request extraction."""

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    ).with_structured_output(ExtractedRequest)


class RequestExtractor:
    """
    LLM language understanding.

    question
      → intent
      → metric
      → ReservationQuery

    The extractor keeps user wording and never invents warehouse IDs.
    """

    def __init__(self, settings: Settings):
        settings.require_llm()
        self.llm = _build_llm(settings)

    def extract(self, question: str) -> ExtractedRequest:
        return self.llm.invoke(
            f"""
Classify and extract this Reservation Analytics request.

Intent:
- knowledge: definitions, metric rules, metadata, grain, fields, tables
- analytics: counts, rates, user lists, campaign results

Metric:
summary | reserved_users | ordered_users |
reserved_not_ordered | conversion_rate

Rules:
- Keep country, product, and campaign wording from the user.
- Only keep an ID/code when the user explicitly supplied it.
- Never invent missing IDs.

Question:
{question}
""".strip()
        )
