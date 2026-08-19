"""Coordinate country, product, and campaign resolution into one stable context.

Resolution order:
    Country -> Product -> Campaign -> CampaignContext

The order lets later lookups use stable IDs discovered by earlier lookups.
"""

from __future__ import annotations

from app.analytics.models.request import ReservationQuery
from app.analytics.models.result import ResolutionResult
from app.analytics.query.backend import QueryBackend
from app.analytics.resolution.campaign_resolver import resolve_campaign
from app.analytics.resolution.country_resolver import resolve_country
from app.analytics.resolution.product_resolver import resolve_product
from app.analytics.resolution.repository import DimensionRepository


class BusinessResolver:
    """Turn extracted business wording into stable governed analytics context.

    Core rule:
        Stable IDs -> exact validation.
        Natural-language names -> resolve only when needed.
    """

    def __init__(self, backend: QueryBackend):
        """Create the governed dimension repository used by all resolvers."""
        self.repo = DimensionRepository(backend)

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        """Resolve one structured query into ``CampaignContext``.

        Args:
            raw_query: Business context extracted by the LLM.

        Returns:
            ``ResolutionResult`` containing either stable context or a reason
            that the workflow must stop.

        Flow:
            ReservationQuery
                -> resolve country
                -> resolve product
                -> resolve campaign
                -> CampaignContext
        """
        # Work on a copy so the caller's original object is not mutated.
        query = raw_query.model_copy(deep=True)

        # ----- 1. Country -----
        status, items = resolve_country(query, self.repo)
        if status != 'ok':
            return self._stop(query, 'country', status, items)

        # Normalize the natural-language country to its governed code/name.
        if items:
            query.country_code = items[0].entity_id
            query.country = items[0].name

        # ----- 2. Product -----
        status, items = resolve_product(query, self.repo)
        if status != 'ok':
            return self._stop(query, 'product', status, items)

        if items:
            query.product_id = items[0].entity_id
            query.product = items[0].name

        # ----- 3. Campaign -----
        # Campaign resolution uses the stable country/product IDs found above.
        status, context, items = resolve_campaign(query, self.repo)
        if status != 'ok' or context is None:
            return self._stop(query, 'campaign', status, items)

        # Copy the governed context back into the normalized query.
        query.campaign_id = context.campaign_id
        query.campaign_name = context.campaign_name
        query.country_code = context.country_code
        query.country = context.country_name

        return ResolutionResult(
            status='resolved',
            query=query,
            context=context,
        )

    @staticmethod
    def _stop(query, entity: str, status: str, candidates):
        """Convert resolver failure/ambiguity into one consistent result object."""
        if status == 'ambiguous':
            choices = ', '.join(
                f'{candidate.entity_id} ({candidate.name})'
                for candidate in candidates[:8]
            )
            return ResolutionResult(
                status='clarification',
                query=query,
                candidates=candidates[:8],
                message=(
                    f'Multiple {entity}s matched. '
                    f'Please retry with one stable ID: {choices}.'
                ),
            )

        return ResolutionResult(
            status='not_found',
            query=query,
            message=f'No governed {entity} matched the request.',
        )
