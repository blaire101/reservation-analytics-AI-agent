from __future__ import annotations

import re

from app.settings import Settings


class KnowledgeRAG:
    """Retrieves business-metric and data-model knowledge."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.text = "\n\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(settings.knowledge_dir.glob("*.md"))
        )
        self._engine = None

    def _build_engine(self):
        if self._engine is not None:
            return self._engine
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_ENABLED=true.")

        import faiss
        from llama_index.core import Settings as LlamaSettings
        from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI
        from llama_index.vector_stores.faiss import FaissVectorStore

        LlamaSettings.embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,
            api_key=self.settings.openai_api_key,
        )
        LlamaSettings.llm = OpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )
        documents = SimpleDirectoryReader(
            input_dir=str(self.settings.knowledge_dir),
            required_exts=[".md"],
        ).load_data()

        vector_store = FaissVectorStore(faiss_index=faiss.IndexFlatL2(1536))
        storage = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(documents, storage_context=storage)
        self._engine = index.as_query_engine(similarity_top_k=3)
        return self._engine

    def _local_answer(self, question: str) -> str:
        low = question.lower()
        if "reserved" in low and ("not ordered" in low or "did not order" in low):
            return "A reserved-but-not-ordered user has freserve_flag=1 and forder_flag=0."
        if "conversion" in low:
            return "Reservation-to-order conversion rate is Ordered Users divided by Reserved Users for the same Campaign + Product + Country context."
        if "grain" in low:
            return "dm_reservation_subject_df has grain User × Campaign × Product × Country."

        sections = re.split(r"(?m)^##\s+", self.text)
        tokens = {x for x in re.findall(r"[a-z0-9_-]+", low) if len(x) > 2}
        ranked = sorted(sections, key=lambda s: sum(t in s.lower() for t in tokens), reverse=True)
        lines = [line.strip() for line in ranked[0].splitlines() if line.strip()]
        return " ".join(lines[:6])[:900]

    def answer(self, question: str) -> str:
        if not self.settings.use_llm:
            return self._local_answer(question)
        return str(self._build_engine().query(question))
