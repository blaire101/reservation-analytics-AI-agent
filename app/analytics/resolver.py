from __future__ import annotations

import json

from app.analytics.repository import DimensionRepository
from app.core.models import (
    EntityCandidate,
    MatchDecision,
    ReservationQuery,
    ResolutionResult,
)
from app.data.backend import QueryBackend
from app.settings import Settings


def _build_llm(settings: Settings):
    """Create the structured LLM used only for governed candidate selection."""

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    ).with_structured_output(MatchDecision)


class CampaignResolver:
    """
    Ground user wording to governed IDs.

    Flow:
        country if supplied
          → product if supplied
          → campaign
          → CampaignContext

    Ambiguous:
        return candidates → user confirms → continue resolve()

    A campaign may contain many products, so product is optional.
    """

    def __init__(self, backend: QueryBackend, settings: Settings):
        settings.require_llm()
        self.repo = DimensionRepository(backend)
        self.llm = _build_llm(settings)

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)

        for entity_type, mention, candidates in (
            (
                "country",
                query.country_code or query.country,
                self.repo.list_countries(),
            ),
            (
                "product",
                query.product_id or query.product,
                self.repo.list_products(),
            ),
        ):
            pending = self._resolve_optional(
                query,
                entity_type,
                mention,
                candidates,
            )
            if pending:
                return pending

        return self._resolve_campaign(query)

    def confirm(
        self,
        entity_type: str,
        user_answer: str,
        candidates: list[EntityCandidate],
        raw_query: ReservationQuery,
    ) -> ResolutionResult:
        """Resolve one clarification reply, then continue the normal flow."""

        query = raw_query.model_copy(deep=True)

        if user_answer.strip().isdigit():
            index = int(user_answer.strip()) - 1
            if 0 <= index < len(candidates):
                self._set(query, entity_type, candidates[index])
                return self.resolve(query)

        chosen = self._choose(entity_type, user_answer, candidates, query)
        if isinstance(chosen, ResolutionResult):
            return chosen

        self._set(query, entity_type, chosen)
        return self.resolve(query)

    def _resolve_optional(
        self,
        query: ReservationQuery,
        entity_type: str,
        mention: str | None,
        candidates: list[EntityCandidate],
    ) -> ResolutionResult | None:
        if not mention:
            return None

        chosen = self._choose(entity_type, mention, candidates, query)
        if isinstance(chosen, ResolutionResult):
            return chosen

        self._set(query, entity_type, chosen)
        return None

    def _resolve_campaign(self, query: ReservationQuery) -> ResolutionResult:
        candidates = self.repo.list_campaigns(query)
        if not candidates:
            return self._not_found(query, "No campaign matched this context.")

        mention = query.campaign_id or query.campaign_name

        if mention:
            chosen = self._choose("campaign", mention, candidates, query)
            if isinstance(chosen, ResolutionResult):
                return chosen
        elif len(candidates) == 1:
            chosen = candidates[0]
        else:
            return self._clarify(query, "campaign", candidates)

        query.campaign_id = chosen.entity_id
        query.campaign_name = chosen.name

        context = self.repo.get_context(
            campaign_id=chosen.entity_id,
            country_code=query.country_code,
            product_id=query.product_id,
        )
        if context is None:
            return self._not_found(
                query,
                "Campaign context is still ambiguous. Please provide country.",
            )

        query.country_code = context.country_code
        query.country = context.country_name

        return ResolutionResult(
            status="resolved",
            query=query,
            context=context,
        )

    def _choose(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
        query: ReservationQuery,
    ) -> EntityCandidate | ResolutionResult:
        """LLM can choose only IDs returned by governed dimensions."""

        if not candidates:
            return self._not_found(
                query,
                f"No governed {entity_type} candidates were found.",
            )

        allowed = [item.model_dump() for item in candidates[:100]]
        decision = self.llm.invoke(
            f"""
Match this {entity_type}.

User wording:
{mention}

Allowed candidates:
{json.dumps(allowed, ensure_ascii=False)}

Return selected_id only when one candidate is clear.
Otherwise return plausible candidate_ids.
Never invent an ID.
""".strip()
        )

        by_id = {item.entity_id: item for item in candidates}

        if decision.selected_id in by_id:
            return by_id[decision.selected_id]

        choices = [
            by_id[item]
            for item in decision.candidate_ids
            if item in by_id
        ]
        if choices:
            return self._clarify(query, entity_type, choices)

        return self._not_found(
            query,
            f"No governed {entity_type} matched {mention!r}.",
        )

    @staticmethod
    def _set(
        query: ReservationQuery,
        entity_type: str,
        candidate: EntityCandidate,
    ) -> None:
        if entity_type == "country":
            query.country_code, query.country = candidate.entity_id, candidate.name
        elif entity_type == "product":
            query.product_id, query.product = candidate.entity_id, candidate.name
        else:
            query.campaign_id, query.campaign_name = candidate.entity_id, candidate.name

    @staticmethod
    def _clarify(
        query: ReservationQuery,
        entity_type: str,
        candidates: list[EntityCandidate],
    ) -> ResolutionResult:
        candidates = candidates[:8]
        choices = "; ".join(
            f"{i}. {item.entity_id} — {item.name}"
            for i, item in enumerate(candidates, start=1)
        )
        return ResolutionResult(
            status="clarification",
            query=query,
            pending_entity=entity_type,
            candidates=candidates,
            message=f"Please choose {entity_type}: {choices}",
        )

    @staticmethod
    def _not_found(
        query: ReservationQuery,
        message: str,
    ) -> ResolutionResult:
        return ResolutionResult(
            status="not_found",
            query=query,
            message=message,
        )
