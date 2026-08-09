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
        """
        Build and cache the LlamaIndex RAG query engine. （Create index from documents）
        Flow:
            Markdown knowledge files
            -> LlamaIndex Documents
            -> text chunks / nodes
            -> OpenAI embeddings
            -> FAISS vector index
            -> similarity retrieval
            -> OpenAI LLM
            -> final answer

        FAISS
            = vector similarity search
            = nearest-neighbor search
            = mainly for embeddings
        """

        # Reuse the existing engine once it has been initialized.
        if self._engine is not None:
            return self._engine

        # LLM and embedding calls require a valid OpenAI API key.
        if not self.settings.openai_api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is required when LLM_ENABLED=true."
            )

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

        # Configure the embedding model used to convert
        # knowledge chunks and user questions into vectors.
        LlamaSettings.embed_model = OpenAIEmbedding(
            model=self.settings.embedding_model,  # "text-embedding-3-small"
            api_key=self.settings.openai_api_key,
        )

        # Configure the LLM used to generate the final grounded answer.
        # temperature=0 keeps the output more deterministic and consistent.
        LlamaSettings.llm = OpenAI(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )

        # Load all Markdown files from the knowledge directory
        # as LlamaIndex Document objects.
        documents = SimpleDirectoryReader(
            input_dir=str(self.settings.knowledge_dir),
            required_exts=[".md"],
        ).load_data()

        # Create an in-memory FAISS index.
        # IndexFlatL2 uses L2 / Euclidean distance for vector similarity search.
        # 1536 matches the default embedding dimension of text-embedding-3-small.
        vector_store = FaissVectorStore(
            faiss_index=faiss.IndexFlatL2(1536)
        )

        # Connect LlamaIndex storage to the FAISS vector store.
        storage = StorageContext.from_defaults(
            vector_store=vector_store
        )

        # Build the vector index:
        # Documents -> chunks/nodes -> embeddings -> FAISS.
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage,
        )

        # Create the query engine.
        # For each question, retrieve the top 3 most similar chunks
        # and provide them as context to the LLM.
        """
        Chunk1 ┐
        Chunk2 ├→ Context → LLM → 1 Answer
        Chunk3 ┘
        """
        self._engine = index.as_query_engine(
            similarity_top_k=3
        )

        return self._engine

    def _local_answer(self, question: str) -> str:
        low = question.lower()
        if "reserved" in low and ("not ordered" in low or "did not order" in low):
            return "A reserved-but-not-ordered user has freserve_flag=1 and forder_flag=0."
        if "conversion" in low:
            return "Reservation-to-order conversion rate is Ordered Users divided by Reserved Users for the same Campaign + Product + Country context."
        if "grain" in low:
            return "dm_reservation_subject_df has grain User × Campaign × Product × Country."

        return "Please refer to the project knowledge documentation."

    def answer(self, question: str) -> str:
        if not self.settings.use_llm:
            return self._local_answer(question)
        return str(self._build_engine().query(question))
