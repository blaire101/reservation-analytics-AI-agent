from __future__ import annotations

from difflib import SequenceMatcher
import json
import re
import unicodedata

from app.core.models import (
    Campaign,
    EntityCandidate,
    EntitySelection,
    ReservationQuery,
    ResolutionResult,
)
from app.data.backend import QueryBackend
from app.settings import Settings


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    value = re.sub(r"[\s_\-]+", " ", value)
    value = re.sub(r"[^\w\s]", "", value, flags=re.UNICODE)
    return re.sub(r"\s+", " ", value).strip()


def missing_context(query: ReservationQuery) -> list[str]:
    if query.campaign_id:
        return []
    missing: list[str] = []
    if not (query.country or query.country_code):
        missing.append("country")
    if not (query.product or query.product_id):
        missing.append("product")
    if not (query.campaign_name or query.campaign_month):
        missing.append("campaign")
    return missing


class CandidateSelector:
    """Conservative entity matcher. IDs always come from supplied dimension candidates."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._llm = None

    @staticmethod
    def _local_score(mention: str, candidate: EntityCandidate) -> float:
        a, b = _norm(mention), _norm(candidate.name)
        if not a or not b:
            return 0.0
        if a == _norm(candidate.entity_id):
            return 1.0
        if a == b:
            return 0.99
        # Ignore generic display words for simple product phrasing such as
        # "Mi 17" vs "Phone Mi 17". This is normalization, not an alias catalog.
        generic = {"phone", "smartphone"}
        a_simple = " ".join(t for t in a.split() if t not in generic)
        b_simple = " ".join(t for t in b.split() if t not in generic)
        if a_simple and a_simple == b_simple:
            return 0.985
        ratio = SequenceMatcher(None, a, b).ratio()
        a_tokens, b_tokens = set(a.split()), set(b.split())
        overlap = len(a_tokens & b_tokens) / max(1, len(a_tokens))
        containment = 0.92 if a in b else 0.0
        return max(ratio, overlap * 0.85, containment)

    def _local_select(self, mention: str, candidates: list[EntityCandidate]) -> EntitySelection:
        if not candidates:
            return EntitySelection(status="not_found", reason="No governed candidates are available.")

        exact_id = [c for c in candidates if _norm(c.entity_id) == _norm(mention)]
        if len(exact_id) == 1:
            return EntitySelection(status="resolved", selected_id=exact_id[0].entity_id, candidate_ids=[exact_id[0].entity_id])

        ranked = sorted(
            ((self._local_score(mention, c), c) for c in candidates),
            key=lambda item: item[0],
            reverse=True,
        )
        top_score, top = ranked[0]
        second_score = ranked[1][0] if len(ranked) > 1 else 0.0
        if top_score >= 0.96 or (top_score >= 0.78 and top_score - second_score >= 0.08):
            return EntitySelection(status="resolved", selected_id=top.entity_id, candidate_ids=[top.entity_id])

        plausible = [c.entity_id for score, c in ranked[:5] if score >= 0.45]
        if not plausible:
            plausible = [c.entity_id for _, c in ranked[:5]]
        return EntitySelection(status="ambiguous", candidate_ids=plausible, reason="No unique lexical match.")

    def select(self, entity_type: str, mention: str, candidates: list[EntityCandidate]) -> EntitySelection:
        local = self._local_select(mention, candidates)
        if local.status == "resolved" or not self.settings.use_llm:
            return local

        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for multilingual semantic entity resolution.")
        if self._llm is None:
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            ).with_structured_output(EntitySelection)

        payload = [c.model_dump() for c in candidates[:100]]
        prompt = f"""You are a conservative multilingual business-entity resolver.
Entity type: {entity_type}
User mention: {mention!r}
Governed candidates: {json.dumps(payload, ensure_ascii=False)}

Rules:
1. You may select ONLY IDs from the candidate list. Never invent an ID.
2. The mention may be English, Chinese, mixed language, abbreviated, have extra spaces, or omit generic words.
3. Return resolved only when exactly one candidate clearly matches the user's meaning.
4. If multiple candidates are plausible or the wording is underspecified, return ambiguous and include the plausible candidate IDs.
5. For products, do not silently upgrade a base model to Pro/Ultra when the user did not specify the variant.
6. For campaigns, use name/description plus product/country/time context shown in candidate descriptions.
7. If nothing plausibly matches, return not_found.
"""
        result = self._llm.invoke(prompt)
        valid_ids = {c.entity_id for c in candidates}
        result.candidate_ids = [x for x in result.candidate_ids if x in valid_ids]
        if result.selected_id not in valid_ids:
            result.selected_id = None
            if result.status == "resolved":
                result.status = "not_found"
        return result


class CampaignResolver:
    """Resolve multilingual free text against governed dimensions, then produce stable IDs."""

    def __init__(self, backend: QueryBackend, settings: Settings):
        self.backend = backend
        self.selector = CandidateSelector(settings)

    def _sites(self) -> list[EntityCandidate]:
        rows = self.backend.execute("""
            SELECT fcountry_code AS entity_id, fcountry_name AS name,
                   fregion_name AS description
            FROM dim_site_df
            WHERE fis_active = 1
            ORDER BY fcountry_code
            LIMIT 100
        """.strip())
        return [EntityCandidate(**row) for row in rows]

    def _products(self) -> list[EntityCandidate]:
        rows = self.backend.execute("""
            SELECT fproduct_id AS entity_id, fproduct_name AS name,
                   (fcategory_lv1_id || ' / ' || fcategory_lv2_id || ' / ' || fcategory_lv3_id) AS description
            FROM dim_product_df
            WHERE fis_active = 1
            ORDER BY fproduct_id
            LIMIT 100
        """.strip())
        return [EntityCandidate(**row) for row in rows]

    def _campaign_candidates(self, query: ReservationQuery) -> list[EntityCandidate]:
        filters = ["1=1"]
        if query.country_code:
            filters.append(f"lower(c.fcountry_code) = lower({_quote(query.country_code)})")
        if query.product_id:
            filters.append(f"c.fproduct_id = {_quote(query.product_id)}")
        if query.campaign_year:
            filters.append(f"substr(c.fstart_time, 1, 4) = {_quote(str(query.campaign_year))}")
        if query.campaign_month:
            filters.append(f"substr(c.fstart_time, 6, 2) = {_quote(f'{query.campaign_month:02d}')}")
        sql = f"""
            SELECT c.fcampaign_id AS entity_id,
                   c.fcampaign_name AS name,
                   (c.fcampaign_type || ' | product=' || c.fproduct_id ||
                    ' | country=' || c.fcountry_code || ' | start=' || c.fstart_time) AS description
            FROM dim_campaign_df c
            WHERE {' AND '.join(filters)}
            ORDER BY c.fstart_time, c.fcampaign_id
            LIMIT 100
        """.strip()
        return [EntityCandidate(**row) for row in self.backend.execute(sql)]

    @staticmethod
    def _candidate_message(entity: str, mention: str, candidates: list[EntityCandidate]) -> str:
        choices = "; ".join(
            f"{i + 1}. {c.entity_id} — {c.name}" for i, c in enumerate(candidates[:8])
        )
        return f"I could not safely resolve {entity} {mention!r}. Please choose: {choices}"

    def _resolve_dimension(
        self,
        entity_type: str,
        mention: str,
        candidates: list[EntityCandidate],
        query: ReservationQuery,
    ) -> ResolutionResult | tuple[str, str]:
        selection = self.selector.select(entity_type, mention, candidates)
        by_id = {c.entity_id: c for c in candidates}
        if selection.status == "resolved" and selection.selected_id in by_id:
            c = by_id[selection.selected_id]
            return c.entity_id, c.name
        selected = [by_id[i] for i in selection.candidate_ids if i in by_id] or candidates[:8]
        if selection.status == "not_found":
            return ResolutionResult(
                status="not_found", query=query,
                message=f"No governed {entity_type} matched {mention!r}.",
            )
        return ResolutionResult(
            status="clarification", query=query, pending_entity=entity_type,
            candidates=selected,
            message=self._candidate_message(entity_type, mention, selected),
        )

    def resolve(self, raw_query: ReservationQuery) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)

        # Explicit campaign_id is already a stable governed ID. If it is the
        # only business identifier supplied, derive Product + Country from the
        # campaign dimension instead of asking the user to repeat them.
        if query.campaign_id and not any([
            query.country, query.country_code, query.product, query.product_id,
            query.campaign_name, query.campaign_month, query.campaign_year,
        ]):
            rows = self.backend.execute(f"""
                SELECT c.fcampaign_id AS campaign_id,
                       c.fcampaign_name AS campaign_name,
                       c.fproduct_id AS product_id,
                       p.fproduct_name AS product_name,
                       c.fcountry_code AS country_code,
                       s.fcountry_name AS country_name,
                       c.fstart_time AS start_time,
                       c.fend_time AS end_time
                FROM dim_campaign_df c
                JOIN dim_product_df p ON c.fproduct_id = p.fproduct_id
                JOIN dim_site_df s ON c.fcountry_code = s.fcountry_code
                WHERE lower(c.fcampaign_id) = lower({_quote(query.campaign_id)})
                LIMIT 1
            """.strip())
            if not rows:
                return ResolutionResult(status="not_found", query=query, message=f"Campaign {query.campaign_id!r} was not found.")
            campaign = Campaign(**rows[0])
            query.country, query.country_code = campaign.country_name, campaign.country_code
            query.product, query.product_id = campaign.product_name, campaign.product_id
            query.campaign_id, query.campaign_name = campaign.campaign_id, campaign.campaign_name
            return ResolutionResult(status="resolved", query=query, campaign=campaign)

        # 1) Country -> governed country_code.
        sites = self._sites()
        if query.country_code:
            match = self._resolve_dimension("country", query.country_code, sites, query)
        elif query.country:
            match = self._resolve_dimension("country", query.country, sites, query)
        else:
            match = None
        if isinstance(match, ResolutionResult):
            return match
        if match:
            query.country_code, canonical_country = match
            query.country = canonical_country

        # 2) Product -> governed product_id.
        products = self._products()
        if query.product_id:
            match = self._resolve_dimension("product", query.product_id, products, query)
        elif query.product:
            match = self._resolve_dimension("product", query.product, products, query)
        else:
            match = None
        if isinstance(match, ResolutionResult):
            return match
        if match:
            query.product_id, canonical_product = match
            query.product = canonical_product

        # 3) Campaign is resolved only after product/country context narrows the candidate set.
        campaigns = self._campaign_candidates(query)
        if not campaigns:
            return ResolutionResult(status="not_found", query=query, message="No campaign matched the resolved product/country/time context.")

        if query.campaign_id:
            selection = self._resolve_dimension("campaign", query.campaign_id, campaigns, query)
        elif query.campaign_name:
            selection = self._resolve_dimension("campaign", query.campaign_name, campaigns, query)
        elif len(campaigns) == 1:
            selection = (campaigns[0].entity_id, campaigns[0].name)
        else:
            return ResolutionResult(
                status="clarification", query=query, pending_entity="campaign", candidates=campaigns[:8],
                message=self._candidate_message("campaign", "the supplied time/context", campaigns[:8]),
            )

        if isinstance(selection, ResolutionResult):
            return selection
        query.campaign_id, query.campaign_name = selection

        rows = self.backend.execute(f"""
            SELECT c.fcampaign_id AS campaign_id,
                   c.fcampaign_name AS campaign_name,
                   c.fproduct_id AS product_id,
                   p.fproduct_name AS product_name,
                   c.fcountry_code AS country_code,
                   s.fcountry_name AS country_name,
                   c.fstart_time AS start_time,
                   c.fend_time AS end_time
            FROM dim_campaign_df c
            JOIN dim_product_df p ON c.fproduct_id = p.fproduct_id
            JOIN dim_site_df s ON c.fcountry_code = s.fcountry_code
            WHERE c.fcampaign_id = {_quote(query.campaign_id)}
              AND c.fproduct_id = {_quote(query.product_id or '')}
              AND c.fcountry_code = {_quote(query.country_code or '')}
            LIMIT 1
        """.strip())
        if not rows:
            return ResolutionResult(status="not_found", query=query, message="The resolved IDs do not form a valid Campaign + Product + Country context.")
        return ResolutionResult(status="resolved", query=query, campaign=Campaign(**rows[0]))

    def confirm(
        self,
        entity_type: str,
        user_answer: str,
        candidates: list[EntityCandidate],
        raw_query: ReservationQuery,
    ) -> ResolutionResult:
        query = raw_query.model_copy(deep=True)
        selected = self._resolve_dimension(entity_type, user_answer, candidates, query)
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
