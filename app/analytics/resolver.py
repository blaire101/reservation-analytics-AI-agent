from __future__ import annotations

from app.analytics.repository import DimensionRepository
from app.analytics.selector import CandidateSelector
from app.core.models import EntityCandidate, ReservationQuery, ResolutionResult
from app.data.backend import QueryBackend
from app.settings import Settings


class CampaignResolver:
    """Turn user wording into one governed Campaign + Product + Country context.

    Read this file as the business flow:
    1. Resolve country only when the user supplied one.
    2. Resolve product only when the user supplied one.
    3. Resolve the campaign using those optional filters plus time/name.
    4. Load the chosen campaign and derive any missing product/country IDs.
    """

    def __init__(self, backend: QueryBackend, settings: Settings):
        self.repository = DimensionRepository(backend)
        self.selector = CandidateSelector(settings)

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)

        country_result = self._resolve_optional_country(query)
        if country_result:
            return country_result

        product_result = self._resolve_optional_product(query)
        if product_result:
            return product_result

        campaign_result = self._resolve_campaign(query)
        if isinstance(campaign_result, ResolutionResult):
            return campaign_result

        campaign = self.repository.get_campaign(campaign_result)
        if campaign is None:
            return ResolutionResult(
                status="not_found",
                query=query,
                message=f"Campaign {campaign_result!r} was not found.",
            )

        # The campaign dimension is authoritative for the final business context.
        query.campaign_id = campaign.campaign_id
        query.campaign_name = campaign.campaign_name
        query.product_id = campaign.product_id
        query.product = campaign.product_name
        query.country_code = campaign.country_code
        query.country = campaign.country_name

        return ResolutionResult(status="resolved", query=query, campaign=campaign)

    def confirm(
        self,
        entity_type: str,
        user_answer: str,
        candidates: list[EntityCandidate],
        raw_query: ReservationQuery,
    ) -> ResolutionResult:
        """Apply one clarification answer, then continue normal resolution."""

        query = raw_query.model_copy(deep=True)
        selected = self._select_candidate(
            entity_type,
            user_answer,
            candidates,
            query,
            allow_choice_number=True,
        )
        if isinstance(selected, ResolutionResult):
            return selected

        entity_id, canonical_name = selected
        if entity_type == "country":
            query.country_code, query.country = entity_id, canonical_name
        elif entity_type == "product":
            query.product_id, query.product = entity_id, canonical_name
        else:
            query.campaign_id, query.campaign_name = entity_id, canonical_name

        return self.resolve(query)

    def _resolve_optional_country(
        self,
        query: ReservationQuery,
    ) -> ResolutionResult | None:
        mention = query.country_code or query.country
        if not mention:
            return None

        result = self._select_candidate(
            "country",
            mention,
            self.repository.list_countries(),
            query,
        )
        if isinstance(result, ResolutionResult):
            return result

        query.country_code, query.country = result
        return None

    def _resolve_optional_product(
        self,
        query: ReservationQuery,
    ) -> ResolutionResult | None:
        mention = query.product_id or query.product
        if not mention:
            return None

        result = self._select_candidate(
            "product",
            mention,
            self.repository.list_products(),
            query,
        )
        if isinstance(result, ResolutionResult):
            return result

        query.product_id, query.product = result
        return None

    def _resolve_campaign(
        self,
        query: ReservationQuery,
    ) -> str | ResolutionResult:
        candidates = self.repository.list_campaigns(query)
        if not candidates:
            return ResolutionResult(
                status="not_found",
                query=query,
                message="No campaign matched the supplied business context.",
            )

        mention = query.campaign_id or query.campaign_name
        if mention:
            result = self._select_candidate(
                "campaign",
                mention,
                candidates,
                query,
            )
            if isinstance(result, ResolutionResult):
                return result
            campaign_id, _ = result
            return campaign_id

        if len(candidates) == 1:
            return candidates[0].entity_id

        return self._clarification(
            entity_type="campaign",
            mention="the supplied time/context",
            candidates=candidates[:8],
            query=query,
        )

    def _select_candidate(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
        query: ReservationQuery,
        allow_choice_number: bool = False,
    ) -> tuple[str, str] | ResolutionResult:
        if allow_choice_number:
            numbered_choice = self._numbered_choice(mention, candidates)
            if numbered_choice:
                return numbered_choice.entity_id, numbered_choice.name

        selection = self.selector.select(entity_type, mention, candidates)
        candidates_by_id = {
            candidate.entity_id: candidate for candidate in candidates
        }

        if selection.status == "resolved" and selection.selected_id in candidates_by_id:
            candidate = candidates_by_id[selection.selected_id]
            return candidate.entity_id, candidate.name

        if selection.status == "not_found":
            return ResolutionResult(
                status="not_found",
                query=query,
                message=f"No governed {entity_type} matched {mention!r}.",
            )

        plausible = [
            candidates_by_id[candidate_id]
            for candidate_id in selection.candidate_ids
            if candidate_id in candidates_by_id
        ]
        return self._clarification(
            entity_type=entity_type,
            mention=mention,
            candidates=plausible or candidates[:8],
            query=query,
        )

    @staticmethod
    def _numbered_choice(
        answer: str,
        candidates: list[EntityCandidate],
    ) -> EntityCandidate | None:
        value = answer.strip()
        if not value.isdigit():
            return None
        index = int(value) - 1
        if 0 <= index < len(candidates):
            return candidates[index]
        return None

    @staticmethod
    def _clarification(
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
        query: ReservationQuery,
    ) -> ResolutionResult:
        choices = "; ".join(
            f"{index}. {candidate.entity_id} — {candidate.name}"
            for index, candidate in enumerate(candidates[:8], start=1)
        )
        return ResolutionResult(
            status="clarification",
            query=query,
            pending_entity=entity_type,
            candidates=candidates[:8],
            message=(
                f"I could not safely resolve {entity_type} {mention!r}. "
                f"Please choose: {choices}"
            ),
        )
