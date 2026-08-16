from __future__ import annotations

from app.settings import Settings


class KnowledgeRAG:
    """Answer metric and data-model questions from the project knowledge files."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._engine = None

    def answer(self, question: str) -> str:
        if not self.settings.use_llm:
            return self._offline_answer(question)
        return str(self._get_engine().query(question))

    def _get_engine(self):
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def _build_engine(self):
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required when LLM_ENABLED=true.")

        import faiss
        from llama_index.core import (
            Settings as LlamaSettings,
            SimpleDirectoryReader,
            StorageContext,
            VectorStoreIndex,
        )
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

        # text-embedding-3-small returns 1536 dimensions by default.
        vector_store = FaissVectorStore(
            faiss_index=faiss.IndexFlatL2(1536)
        )
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store
        )
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
        )
        return index.as_query_engine(similarity_top_k=3)

    @staticmethod
    def _offline_answer(question: str) -> str:
        low = question.lower()

        if "reserved" in low and (
            "not ordered" in low or "did not order" in low
        ):
            return (
                "A reserved-but-not-ordered user has "
                "freserve_flag=1 and forder_flag=0."
            )
        if "conversion" in low:
            return (
                "Reservation-to-order conversion rate is Ordered Users divided "
                "by Reserved Users for the same Campaign + Product + Country context."
            )
        if "grain" in low:
            return (
                "dm_reservation_subject_df has grain "
                "User × Campaign × Product × Country."
            )

        return "Please refer to the project knowledge documentation."
