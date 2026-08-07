from __future__ import annotations

from app.config import AppSettings
from app.prompts import EXTRACTION_SYSTEM_PROMPT
from app.schemas import ExtractedRequest
from app.services.mock_parser import parse_mock_request


class RequestExtractor:
    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._structured_llm = None

    def _build_real_extractor(self):
        if self._structured_llm is not None:
            return self._structured_llm

        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when MOCK_MODE=false.")

        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )
        self._structured_llm = llm.with_structured_output(ExtractedRequest)
        return self._structured_llm

    def extract(self, question: str) -> ExtractedRequest:
        if self.settings.mock_mode:
            return parse_mock_request(
                question,
                default_year=self.settings.default_campaign_year,
            )

        structured = self._build_real_extractor()
        return structured.invoke(
            [
                ("system", EXTRACTION_SYSTEM_PROMPT),
                ("human", question),
            ]
        )
