"""Controlled SQL builders for reservation summary and detail analytics."""

from app.analytics.models.context import CampaignContext
from app.analytics.query.sql_utils import sql_string


def where_clause(context: CampaignContext) -> str:
    """Build the governed WHERE clause from stable resolved IDs.

    Args:
        context: ``CampaignContext`` produced by entity resolution.

    Returns:
        SQL filter string scoped by campaign and country, plus product when
        present.

    Important:
        This function receives stable IDs, not raw natural-language wording.
    """
    filters = [
        f'fcampaign_id = {sql_string(context.campaign_id)}',
        f'fcountry_code = {sql_string(context.country_code)}',
    ]

    if context.product_id:
        filters.append(f'fproduct_id = {sql_string(context.product_id)}')

    return ' AND '.join(filters)


def summary_sql(context: CampaignContext) -> str:
    """Build the allowlisted aggregate SQL used by summary metrics.

    Returns these trusted measures in one query:
        reserved: distinct users with reservation flag = 1
        ordered: distinct users with order flag = 1
        not_ordered: distinct reserved-but-not-paid users
    """
    return f"""
        SELECT
            COUNT(DISTINCT CASE
                WHEN freserve_flag = 1 THEN fuser_id
            END) AS reserved,
            COUNT(DISTINCT CASE
                WHEN forder_flag = 1 THEN fuser_id
            END) AS ordered,
            COUNT(DISTINCT CASE
                WHEN ftag_reserved_not_paid = 1 THEN fuser_id
            END) AS not_ordered
        FROM dm_reservation_subject_df
        WHERE {where_clause(context)}
    """.strip()


def details_sql(context: CampaignContext) -> str:
    """Build the controlled detail query for reserved-but-not-ordered users.

    Privacy rule:
        Return ``fuser_id_hash`` rather than raw ``fuser_id``.

    Safety rule:
        Limit demo output to at most 100 detail rows.
    """
    return f"""
        SELECT
            fuser_id_hash,
            fcampaign_id,
            fproduct_id,
            fcountry_code
        FROM dm_reservation_subject_df
        WHERE {where_clause(context)}
          AND ftag_reserved_not_paid = 1
        ORDER BY fuser_id_hash
        LIMIT 100
    """.strip()
