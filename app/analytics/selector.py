from __future__ import annotations

from difflib import SequenceMatcher
import json
import re
import unicodedata

from app.core.models import EntityCandidate, EntitySelection
from app.settings import Settings


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = re.sub(r"[\s_\-]+", " ", value)
    value = re.sub(r"[^\w\s]", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


class CandidateSelector:
    """Choose one governed candidate or return an ambiguous candidate set."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    def select(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
    ) -> EntitySelection:
        local = self._select_locally(mention, candidates)
        if local.status == "resolved" or not self.settings.use_llm:
            return local
        return self._select_with_llm(entity_type, mention, candidates)

    def _select_locally(
        self,
        mention: str,
        candidates: list[EntityCandidate],
    ) -> EntitySelection:
        if not candidates:
            return EntitySelection(status="not_found", reason="No governed candidates.")

        mention_norm = normalize_text(mention)
        exact_id = [
            c for c in candidates if normalize_text(c.entity_id) == mention_norm
        ]
        if len(exact_id) == 1:
            candidate = exact_id[0]
            return EntitySelection(
                status="resolved",
                selected_id=candidate.entity_id,
                candidate_ids=[candidate.entity_id],
            )

        ranked = sorted(
            ((self._score(mention, candidate), candidate) for candidate in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        top_score, top_candidate = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0

        clear_match = top_score >= 0.96 or (
            top_score >= 0.78 and top_score - second_score >= 0.08
        )
        if clear_match:
            return EntitySelection(
                status="resolved",
                selected_id=top_candidate.entity_id,
                candidate_ids=[top_candidate.entity_id],
            )

        plausible = [
            candidate.entity_id
            for score, candidate in ranked[:5]
            if score >= 0.45
        ]
        if not plausible:
            plausible = [candidate.entity_id for _, candidate in ranked[:5]]

        return EntitySelection(
            status="ambiguous",
            candidate_ids=plausible,
            reason="No unique lexical match.",
        )

    @staticmethod
    def _score(mention: str, candidate: EntityCandidate) -> float:
        left = normalize_text(mention)
        right = normalize_text(candidate.name)
        if not left or not right:
            return 0.0
        if left == right:
            return 0.99

        generic_words = {"phone", "smartphone"}
        left_simple = " ".join(
            word for word in left.split() if word not in generic_words
        )
        right_simple = " ".join(
            word for word in right.split() if word not in generic_words
        )
        if left_simple and left_simple == right_simple:
            return 0.985

        ratio = SequenceMatcher(None, left, right).ratio()
        left_tokens = set(left.split())
        right_tokens = set(right.split())
        token_overlap = len(left_tokens & right_tokens) / max(1, len(left_tokens))
        containment = 0.92 if left in right else 0.0
        return max(ratio, token_overlap * 0.85, containment)

    def _select_with_llm(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
    ) -> EntitySelection:
        if not self.settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required for multilingual semantic entity resolution."
            )

        if self._llm is None:
            from langchain_openai import ChatOpenAI

            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(EntitySelection)

        payload = [candidate.model_dump() for candidate in candidates[:100]]
        prompt = f"""Resolve one business entity from governed candidates.
Entity type: {entity_type}
User mention: {mention!r}
Candidates: {json.dumps(payload, ensure_ascii=False)}

Rules:
- Select only IDs that appear in Candidates. Never invent an ID.
- The mention may be multilingual, abbreviated, or contain irregular spacing.
- Return resolved only when one candidate clearly matches.
- Return ambiguous when several candidates remain plausible.
- For products, never infer Pro/Ultra when the user did not specify the variant.
- Return not_found when nothing plausibly matches.
"""
        result = self._llm.invoke(prompt)
        return self._keep_only_governed_ids(result, candidates)

    @staticmethod
    def _keep_only_governed_ids(
        result: EntitySelection,
        candidates: list[EntityCandidate],
    ) -> EntitySelection:
        valid_ids = {candidate.entity_id for candidate in candidates}
        result.candidate_ids = [
            candidate_id
            for candidate_id in result.candidate_ids
            if candidate_id in valid_ids
        ]
        if result.selected_id not in valid_ids:
            result.selected_id = None
            if result.status == "resolved":
                result.status = "not_found"
        return result
