from __future__ import annotations

import re

from app.settings import Settings


class KnowledgeRAG:
    """Business knowledge retrieval: LlamaIndex + FAISS in LLM mode."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.text = settings.knowledge_file.read_text(encoding="utf-8")
        self._engine = None

    def _build_engine(self):
        if self._engine is not None:
            return self._engine
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when USE_LLM=true.")

        import faiss
        from llama_index.core import Settings as LlamaSettings
        from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI
        from llama_index.vector_stores.faiss import FaissVectorStore

        embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,
            api_key=self.settings.openai_api_key,
        )
        LlamaSettings.embed_model = embed_model
        LlamaSettings.llm = OpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )

        documents = SimpleDirectoryReader(
            input_dir=str(self.settings.knowledge_dir),
            required_exts=[".md"],
        ).load_data()

        # text-embedding-3-small defaults to 1536 dimensions.
        vector_store = FaissVectorStore(faiss_index=faiss.IndexFlatL2(1536))
        storage = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex.from_documents(documents, storage_context=storage)
        self._engine = index.as_query_engine(similarity_top_k=3)
        return self._engine

    def _local_answer(self, question: str) -> str:
        """Small deterministic fallback so the default project runs without an API key."""
        low = question.lower()
        if "reserved" in low and ("not ordered" in low or "did not order" in low):
            return (
                "A reserved-but-not-ordered user has a reservation in the selected "
                "campaign context but no matching order in that campaign window."
            )
        if "conversion" in low:
            return (
                "Reservation-to-order conversion rate is Ordered Users divided by "
                "Reserved Users for the same resolved campaign context."
            )
        if "grain" in low:
            return (
                "The Reservation Data Mart grain is User × Campaign × Product × Site."
            )

        sections = re.split(r"(?m)^##\s+", self.text)
        tokens = {x for x in re.findall(r"[a-z0-9_-]+", low) if len(x) > 2}
        ranked = sorted(
            sections,
            key=lambda section: sum(t in section.lower() for t in tokens),
            reverse=True,
        )
        lines = [line.strip() for line in ranked[0].splitlines() if line.strip()]
        return " ".join(lines[:5])[:800]

    def answer(self, question: str) -> str:
        if not self.settings.use_llm:
            return self._local_answer(question)
        return str(self._build_engine().query(question))
