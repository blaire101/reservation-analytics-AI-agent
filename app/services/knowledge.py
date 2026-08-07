from __future__ import annotations

import re
from app.config import AppSettings


class KnowledgeService:
    """
    Real mode:
        reservation_analytics.md -> LlamaIndex -> vector index -> query engine

    Mock mode:
        a tiny deterministic Markdown retriever is used so the project can be
        demonstrated locally without an API key. The production code path
        remains LlamaIndex.
    """

    def __init__(self, settings: AppSettings):
        self.settings = settings
        self._query_engine = None
        self._markdown = settings.knowledge_file.read_text(encoding="utf-8")

    def _build_llamaindex(self):
        if self._query_engine is not None:
            return self._query_engine

        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for LlamaIndex real mode.")

        from llama_index.core import Settings, SimpleDirectoryReader, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI

        Settings.llm = OpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )
        Settings.embed_model = OpenAIEmbedding(
            model=self.settings.openai_embedding_model,
            api_key=self.settings.openai_api_key,
        )

        documents = SimpleDirectoryReader(
            input_files=[str(self.settings.knowledge_file)]
        ).load_data()

        index = VectorStoreIndex.from_documents(documents)
        self._query_engine = index.as_query_engine(similarity_top_k=3)
        return self._query_engine

    def _mock_answer(self, question: str) -> str:
        low = question.lower()

        if "reserved-but-not-ordered" in low or "reserved but not ordered" in low:
            return (
                "A reserved-but-not-ordered user is a user who has a reservation "
                "for the selected campaign context but has no corresponding order "
                "within the approved campaign analysis window."
            )

        if "conversion rate" in low and ("calculate" in low or "calculated" in low or "how is" in low):
            return (
                "Reservation-to-Order Conversion Rate = Ordered Users / Reserved Users. "
                "Both counts must use the same resolved campaign context and campaign period."
            )

        if "grain" in low:
            return (
                "The DM grain is User × Campaign × Product × Site. One row represents "
                "one user's activity for one campaign, one product, and one site."
            )

        # Minimal section-scoring fallback for other knowledge questions.
        sections = re.split(r"(?m)^##\s+", self._markdown)
        tokens = {x for x in re.findall(r"[a-z0-9_-]+", low) if len(x) > 2}
        scored = []
        for sec in sections:
            sec_low = sec.lower()
            score = sum(1 for t in tokens if t in sec_low)
            scored.append((score, sec.strip()))
        scored.sort(reverse=True, key=lambda x: x[0])
        best = scored[0][1] if scored else self._markdown
        # Keep mock answer concise.
        lines = [x.strip() for x in best.splitlines() if x.strip()]
        return " ".join(lines[:5])[:900]

    def answer(self, question: str) -> str:
        if self.settings.mock_mode:
            return self._mock_answer(question)

        engine = self._build_llamaindex()
        return str(engine.query(question))
