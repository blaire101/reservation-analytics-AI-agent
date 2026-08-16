from __future__ import annotations

import json
import re
import unicodedata

from pydantic import BaseModel, Field

from app.core.models import EntityCandidate
from app.settings import Settings


class MatchResult(BaseModel):
    selected_id: str | None = None
    candidate_ids: list[str] = Field(default_factory=list)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).lower()
    value = re.sub(r"[^\w\s]", " ", value)
    words = [w for w in value.split() if w not in {"phone", "smartphone"}]
    return " ".join(words)


class CandidateMatcher:
    """Exact match → unique partial match → optional LLM → clarification."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def match(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
    ) -> MatchResult:
        target = normalize(mention)

        exact = [
            c for c in candidates
            if normalize(c.entity_id) == target or normalize(c.name) == target
        ]
        if len(exact) == 1:
            return MatchResult(selected_id=exact[0].entity_id)

        partial = [
            c for c in candidates
            if target and (
                target in normalize(c.name)
                or normalize(c.name) in target
            )
        ]
        if len(partial) == 1:
            return MatchResult(selected_id=partial[0].entity_id)

        choices = partial or candidates
        if not self.settings.use_llm:
            return MatchResult(candidate_ids=[c.entity_id for c in choices[:8]])

        return self._llm_match(entity_type, mention, choices)

    def _llm_match(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
    ) -> MatchResult:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_ENABLED=true.")

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(MatchResult)

        allowed = [c.model_dump() for c in candidates[:100]]
        result = self._llm.invoke(
            f"""Choose one governed {entity_type} candidate.

User wording: {mention!r}
Candidates: {json.dumps(allowed, ensure_ascii=False)}

Rules:
- selected_id must come from Candidates.
- Never invent an ID.
- If not clear, return plausible candidate_ids.
"""
        )

        valid = {c.entity_id for c in candidates}
        if result.selected_id not in valid:
            result.selected_id = None
        result.candidate_ids = [x for x in result.candidate_ids if x in valid]
        return result
