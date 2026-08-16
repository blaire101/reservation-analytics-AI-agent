from __future__ import annotations

from app.settings import Settings


class KnowledgeRAG:
    """
    Answer knowledge questions from project documents.

    Flow:
        documents → embeddings → FAISS → Top-K → LLM answer
    """

    def __init__(self, settings: Settings):
        settings.require_llm()
        self.settings = settings
        self._engine = None

    def answer(self, question: str) -> str:
        return str(self._get_engine().query(question))

    def _get_engine(self):
        if self._engine is None:
            self._engine = self._build_engine()
        return self._engine

    def _build_engine(self):
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

        # text-embedding-3-small uses 1536 dimensions by default.
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
