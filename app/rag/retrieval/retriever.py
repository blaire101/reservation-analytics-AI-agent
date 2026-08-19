"""RAG retrieval: connect Documents, embeddings, FAISS, Top-K, and the LLM."""

from llama_index.core import StorageContext, VectorStoreIndex


def build_query_engine(
    documents,
    vector_store,
    embed_model,
    llm,
    top_k: int = 3,
):
    """Build a LlamaIndex query engine for retrieval and answer generation.

    Args:
        documents:
            Loaded LlamaIndex Document objects that will be indexed.
        vector_store:
            Vector database used to store document embeddings, here FAISS.
        embed_model:
            Embedding model that converts document chunks and user queries
            into vectors.
        llm:
            Language model that generates the final answer using retrieved
            context.
        top_k:
            Number of most relevant chunks retrieved for each query. For
            example, ``top_k=3`` sends the three closest chunks to the LLM.

    Key objects:
        StorageContext:
            Tells LlamaIndex where the generated vectors should be stored.
        VectorStoreIndex.from_documents():
            Processes the Documents, creates searchable chunks/nodes, embeds
            them, and builds the vector-backed index.
        as_query_engine():
            Creates the runtime interface used later as
            ``query_engine.query(question)``.

    Returns:
        A LlamaIndex query engine ready for RAG questions.

    Flow:
        Documents
            -> chunks/nodes
            -> embeddings
            -> FAISS vector store

        User Query
            -> query embedding
            -> Top-K similar chunks
            -> LLM + retrieved context
            -> grounded answer
    """
    # Tell LlamaIndex to use our FAISS vector store for embeddings.
    storage = StorageContext.from_defaults(
        vector_store=vector_store,
    )

    # Build the searchable vector index from the loaded knowledge documents.
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage,
        embed_model=embed_model,
    )

    # Create the runtime RAG interface used to ask natural-language questions.
    return index.as_query_engine(
        similarity_top_k=top_k,
        llm=llm,
    )
