"""Extraction node: convert natural language into a typed business plan."""

from app.analytics.models.request import ExtractedRequest
from app.llm.client import structured_llm


class RequestExtractor:
    """Use the LLM only for intent understanding and structured extraction.

    Important boundary:
        The LLM may classify intent and extract business wording, but it does
        NOT generate SQL and it must not invent stable business IDs.
    """

    def __init__(self, settings):
        """Create a structured-output LLM that returns ``ExtractedRequest``."""
        self.llm = structured_llm(settings, ExtractedRequest)

    def extract(self, question: str) -> ExtractedRequest:
        """Convert one user question into a small typed business plan.

        Args:
            question: Raw natural-language question.

        Returns:
            ``ExtractedRequest`` containing:
            - intent: knowledge or analytics
            - metric: requested allowlisted metric
            - detail_requested: whether detail rows are requested
            - query: country/product/campaign wording or explicit IDs

        Example:
            "How many users reserved CMP001 in Germany?"
                -> intent='analytics'
                -> metric='reserved_users'
                -> campaign_id='CMP001'
                -> country='Germany'

        Flow:
            Question -> LLM -> Pydantic structured output
        """
        prompt = f"""
Classify and extract this Reservation Analytics request.
Intent: knowledge or analytics.
Metric: summary | reserved_users | ordered_users | reserved_not_ordered | conversion_rate.
Keep natural-language names as names. Keep ID/code fields only when the user explicitly supplied them.
Never invent an ID and never generate SQL.
Question: {question}
""".strip()

        return self.llm.invoke(prompt)


def run(extractor, state):
    """
        LangGraph node wrapper that stores extraction results in shared state.
        state = LangGraph workflow
    """
    request = extractor.extract(state['question'])

    # LangGraph state uses plain dictionaries, so convert the Pydantic query.
    return {
        **state,
        'intent': request.intent,
        'metric': request.metric,
        'detail_requested': request.detail_requested,
        'query': request.query.model_dump(),
    }
# {
#     state = graph.state AgentState
#
#     "question": "How many users reserved CMP001 in Germany?",
#     "resolved_context": {
#         "campaign_id": "CMP001",
#         "country_code": "DE"
#     }
#
#     "intent": "analytics",
#     "metric": "reserved_users",
#     "detail_requested": False,
#     "query": {
#         "country": "Germany",
#         "country_code": None,
#
#         "product": None,
#         "product_id": None,
#
#         "campaign_name": None,
#         "campaign_id": "CMP001",
#
#         "campaign_month": None,
#         "campaign_year": None
#     }
# }

# -----------------------------------

# request.query = ReservationQuery(
#     campaign_id="CMP001",
#     campaign_name=None,
#     country="Germany",
#     country_code=None,
#     product=None,
#     product_id=None,
#     campaign_month=None,
#     campaign_year=None,
# )