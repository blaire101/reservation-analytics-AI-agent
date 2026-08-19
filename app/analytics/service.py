"""Trusted analytics service that owns allowlisted metric execution.

Important boundary:
    The LLM decides *what the user wants*.
    This service decides *how trusted data is queried*.

The LLM never writes the final SQL.
"""

from __future__ import annotations

from app.analytics.metrics.registry import ALLOWED_METRICS
from app.analytics.metrics.reservation import details_sql, summary_sql
from app.analytics.models.context import CampaignContext
from app.analytics.query.backend import QueryBackend


class AnalyticsService:
    """Execute controlled reservation metrics against a trusted Data Mart."""

    def __init__(self, backend: QueryBackend):
        """Store the backend used to run application-controlled SQL."""
        self.backend = backend

    def run(
        self,
        metric: str,
        context: CampaignContext,
        detail_requested: bool = False,
    ) -> str:
        """Execute one allowlisted metric and format a business-friendly answer.

        Args:
            metric: Allowlisted metric selected by structured output.
            context: Stable campaign/country/product IDs from entity resolution.
            detail_requested: Whether the caller wants reserved-not-ordered
                detail records instead of only an aggregate number.

        Returns:
            Human-readable trusted analytics answer.

        Flow:
            metric + stable context
                -> choose controlled SQL
                -> QueryBackend.execute()
                -> calculate/format metric
                -> answer
        """
        # Defense in depth: never execute an unknown metric name.
        if metric not in ALLOWED_METRICS:
            raise ValueError(f'Unsupported metric: {metric}')

        # ----- Detail path -----
        # Only reserved_not_ordered exposes detail rows in this demo.
        if detail_requested and metric == 'reserved_not_ordered':
            rows = self.backend.execute(details_sql(context))

            # Privacy: detail SQL returns hashed user identifiers only.
            hashes = ', '.join(row['fuser_id_hash'] for row in rows)

            return (
                f'{len(rows)} detail records. '
                f'fuser_id_hash: {hashes or "none"}.'
            )

        # ----- Aggregate path -----
        # One controlled SQL query returns all base counts used by the metrics.
        rows = self.backend.execute(summary_sql(context))
        row = rows[0] if rows else {}

        reserved = int(row.get('reserved') or 0)
        ordered = int(row.get('ordered') or 0)
        not_ordered = int(row.get('not_ordered') or 0)

        # Avoid division by zero when a campaign has no reserved users.
        conversion = ordered / reserved * 100 if reserved else 0

        # Build a readable scope using governed names/IDs.
        scope = (
            f'{context.campaign_id} — {context.campaign_name} '
            f'({context.country_name})'
        )
        if context.product_name:
            scope += f', {context.product_name}'

        # Map each allowlisted metric to its final business sentence.
        messages = {
            'reserved_users': f'{reserved} reserved users.',
            'ordered_users': f'{ordered} ordered users.',
            'reserved_not_ordered': (
                f'{not_ordered} users reserved but did not order.'
            ),
            'conversion_rate': (
                f'reservation-to-order conversion rate was {conversion:.2f}%.'
            ),
        }

        if metric in messages:
            return f'{scope}: {messages[metric]}'

        # ``summary`` returns all main reservation metrics together.
        return (
            f'{scope}: {reserved} reserved, {ordered} ordered, '
            f'{not_ordered} not ordered, {conversion:.2f}% conversion.'
        )
