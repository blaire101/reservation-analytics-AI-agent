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
    """Create the LLM used to select from governed entity candidates."""

    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    ).with_structured_output(MatchDecision)


class CampaignResolver:
    """
    Convert user wording into governed business IDs.

    Main flow:
        1. Resolve country, if supplied
        2. Resolve product, if supplied
        3. Resolve campaign
        4. Build CampaignContext

    If several candidates are possible:
        → ask the user to clarify
        → save candidates in session memory
        → continue with confirm()

    Product is optional because one campaign can contain multiple products.
    """

    def __init__(self, backend: QueryBackend, settings: Settings):
        settings.require_llm()
        self.repo = DimensionRepository(backend)
        self.llm = _build_llm(settings)

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        """Resolve country → product → campaign."""

        query = raw_query.model_copy(deep=True)

        # 1. Country
        country_result = self._resolve_optional(
            query=query,
            entity_type="country",
            mention=query.country_code or query.country,
            candidates=self.repo.list_countries(),
        )
        if country_result:
            return country_result

        # 2. Product
        product_result = self._resolve_optional(
            query=query,
            entity_type="product",
            mention=query.product_id or query.product,
            candidates=self.repo.list_products(),
        )
        if product_result:
            return product_result

        # 3. Campaign
        return self._resolve_campaign(query)

    def confirm(
        self,
        entity_type: str,
        user_answer: str,
        candidates: list[EntityCandidate],
        raw_query: ReservationQuery,
    ) -> ResolutionResult:
        """
        Handle a clarification reply.

        Example:
            Agent: Please choose campaign: 1. CMP001, 2. CMP002
            User:  1
            → set CMP001
            → continue resolve()
        """

        query = raw_query.model_copy(deep=True)

        # A user can reply with a simple number such as "1".
        if user_answer.strip().isdigit():
            index = int(user_answer.strip()) - 1

            if 0 <= index < len(candidates):
                self._set_entity(
                    query,
                    entity_type,
                    candidates[index],
                )
                return self.resolve(query)

        # Otherwise, ask the LLM to interpret the reply
        # using only the previously saved candidates.
        chosen = self._choose_candidate(
            entity_type=entity_type,
            mention=user_answer,
            candidates=candidates,
            query=query,
        )

        if isinstance(chosen, ResolutionResult):
            return chosen

        self._set_entity(query, entity_type, chosen)
        return self.resolve(query)

    def _resolve_optional(
        self,
        query: ReservationQuery,
        entity_type: str,
        mention: str | None,
        candidates: list[EntityCandidate],
    ) -> ResolutionResult | None:
        """Resolve country/product only when the user supplied one."""

        if not mention:
            return None

        chosen = self._choose_candidate(
            entity_type=entity_type,
            mention=mention,
            candidates=candidates,
            query=query,
        )

        if isinstance(chosen, ResolutionResult):
            return chosen

        self._set_entity(query, entity_type, chosen)
        return None

    def _resolve_campaign(
        self,
        query: ReservationQuery,
    ) -> ResolutionResult:
        """Resolve the campaign after known filters are already grounded."""

        candidates = self.repo.list_campaigns(query)

        if not candidates:
            return self._not_found(
                query,
                "No campaign matched this context.",
            )

        mention = query.campaign_id or query.campaign_name

        # User supplied campaign wording / ID.
        if mention:
            chosen = self._choose_candidate(
                entity_type="campaign",
                mention=mention,
                candidates=candidates,
                query=query,
            )

            if isinstance(chosen, ResolutionResult):
                return chosen

        # No campaign wording, but filtering left exactly one campaign.
        elif len(candidates) == 1:
            chosen = candidates[0]

        # Several campaigns remain, so ask instead of guessing.
        else:
            return self._clarify(
                query,
                "campaign",
                candidates,
            )

        query.campaign_id = chosen.entity_id
        query.campaign_name = chosen.name

        # Build the final stable context used by AnalyticsService.
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

    def _choose_candidate(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
        query: ReservationQuery,
    ) -> EntityCandidate | ResolutionResult:
        """
        Ask the LLM to choose only from governed candidates.

        One clear candidate:
            → return EntityCandidate

        Several plausible candidates:
            → return clarification

        No valid candidate:
            → return not_found
        """

        if not candidates:
            return self._not_found(
                query,
                f"No governed {entity_type} candidates were found.",
            )

        allowed = [
            candidate.model_dump()
            for candidate in candidates[:100]
        ]

        decision = self.llm.invoke(
            f"""
Match this {entity_type}.

User wording:
{mention}

Allowed candidates:
{json.dumps(allowed, ensure_ascii=False)}

Rules:
- Select only from Allowed candidates.
- Never invent an ID.
- If one candidate is clear, return selected_id.
- If several candidates are plausible, leave selected_id empty
  and return candidate_ids.
""".strip()
        )

        candidates_by_id = {
            candidate.entity_id: candidate
            for candidate in candidates
        }

        # Unique match.
        if decision.selected_id in candidates_by_id:
            return candidates_by_id[decision.selected_id]

        # Ambiguous match.
        plausible_candidates = [
            candidates_by_id[candidate_id]
            for candidate_id in decision.candidate_ids
            if candidate_id in candidates_by_id
        ]

        if plausible_candidates:
            return self._clarify(
                query,
                entity_type,
                plausible_candidates,
            )

        return self._not_found(
            query,
            f"No governed {entity_type} matched {mention!r}.",
        )

    @staticmethod
    def _set_entity(
        query: ReservationQuery,
        entity_type: str,
        candidate: EntityCandidate,
    ) -> None:
        """Write one resolved ID and name back into ReservationQuery."""

        if entity_type == "country":
            query.country_code = candidate.entity_id
            query.country = candidate.name

        elif entity_type == "product":
            query.product_id = candidate.entity_id
            query.product = candidate.name

        else:
            query.campaign_id = candidate.entity_id
            query.campaign_name = candidate.name

    @staticmethod
    def _clarify(
        query: ReservationQuery,
        entity_type: str,
        candidates: list[EntityCandidate],
    ) -> ResolutionResult:
        """Return candidate choices instead of guessing."""

        candidates = candidates[:8]

        choices = "; ".join(
            f"{index}. {candidate.entity_id} — {candidate.name}"
            for index, candidate in enumerate(candidates, start=1)
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
        """Return a controlled not-found result."""

        return ResolutionResult(
            status="not_found",
            query=query,
            message=message,
        )
