"""High-level RAG service used by the LangGraph knowledge branch."""

from __future__ import annotations

from app.rag.embeddings.embedder import build_embedding
from app.rag.ingestion.loader import load_documents
from app.rag.retrieval.retriever import build_query_engine
from app.rag.vectorstore.faiss_store import build_vector_store


class KnowledgeRAG:
    """Expose one simple ``answer(question)`` interface for the full RAG stack.

    Build flow (first question only):
        Knowledge .md files
            -> Document objects
            -> embedding model
            -> FAISS vector store
            -> LlamaIndex query engine

    Query flow (every question):
        Question
            -> query embedding
            -> Top-K relevant chunks
            -> LLM + retrieved context
            -> grounded answer
    """

    def __init__(self, settings):
        """Store settings and delay expensive RAG setup until first use."""
        settings.require_llm()
        self.settings = settings
        self._engine = None

    def answer(self, question: str) -> str:
        """Answer one knowledge question with the RAG query engine.

        Args:
            question: Natural-language question about business definitions,
                metric rules, or Data Mart knowledge.

        Returns:
            Grounded LLM answer as a string.
        """
        engine = self._get_engine()
        return str(engine.query(question))

    def _get_engine(self):
        """Build the RAG engine once and reuse it for later questions.

        Returns:
            LlamaIndex query engine connected to Documents, embeddings, FAISS,
            Top-K retrieval, and the answer LLM.

        Why lazy initialization:
            Building embeddings/indexes may be relatively expensive. The
            knowledge path should pay that setup cost only when it is actually
            used, and then reuse the same engine afterward.
        """
        if self._engine is None:
            from llama_index.llms.openai import OpenAI

            # 1. Read project knowledge into LlamaIndex Document objects.
            documents = load_documents(self.settings.knowledge_dir)

            # 2. Create the model that converts text into vectors.
            embed_model = build_embedding(self.settings)

            # 3. Create the FAISS vector store for exact L2 similarity search.
            vector_store = build_vector_store()

            # 4. Create the LLM that synthesizes the final grounded answer.
            llm = OpenAI(
                model=self.settings.openai_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            )

            # 5. Connect everything into one query engine.
            self._engine = build_query_engine(
                documents,
                vector_store,
                embed_model,
                llm,
                top_k=3,
            )

        return self._engine
