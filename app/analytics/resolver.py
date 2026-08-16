from __future__ import annotations

from app.analytics.matcher import CandidateMatcher
from app.analytics.repository import DimensionRepository
from app.core.models import EntityCandidate, ReservationQuery, ResolutionResult
from app.data.backend import QueryBackend
from app.settings import Settings


class CampaignResolver:
    """country? → product? → campaign → stable analytics context"""

    def __init__(self, backend: QueryBackend, settings: Settings):
        self.repo = DimensionRepository(backend)
        self.matcher = CandidateMatcher(settings)

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)

        result = self._resolve_optional(
            query, "country", query.country_code or query.country,
            self.repo.list_countries(),
        )
        if result:
            return result

        result = self._resolve_optional(
            query, "product", query.product_id or query.product,
            self.repo.list_products(),
        )
        if result:
            return result

        return self._resolve_campaign(query)

    def confirm(
        self,
        entity_type: str,
        user_answer: str,
        candidates: list[EntityCandidate],
        raw_query: ReservationQuery,
    ) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)

        if user_answer.strip().isdigit():
            index = int(user_answer.strip()) - 1
            if 0 <= index < len(candidates):
                self._set(query, entity_type, candidates[index])
                return self.resolve(query)

        candidate = self._choose(entity_type, user_answer, candidates, query)
        if isinstance(candidate, ResolutionResult):
            return candidate

        self._set(query, entity_type, candidate)
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

        candidate = self._choose(entity_type, mention, candidates, query)
        if isinstance(candidate, ResolutionResult):
            return candidate

        self._set(query, entity_type, candidate)
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

        # Important: do NOT invent or derive one product when a campaign has many.
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
        match = self.matcher.match(entity_type, mention, candidates)
        by_id = {c.entity_id: c for c in candidates}

        if match.selected_id in by_id:
            return by_id[match.selected_id]

        choices = [by_id[x] for x in match.candidate_ids if x in by_id]
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
            f"{i}. {c.entity_id} — {c.name}"
            for i, c in enumerate(candidates, start=1)
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
