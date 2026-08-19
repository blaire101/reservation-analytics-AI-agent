"""RAG vector store: create the FAISS index used for similarity search."""


def build_vector_store(dimensions: int = 1536):
    """Create a FAISS vector store backed by ``IndexFlatL2``.

    Args:
        dimensions: Number of numeric values in each embedding vector. The
            value MUST match the embedding model's output dimension. For
            example, ``1536`` means every embedding has 1536 numbers.

    What ``IndexFlatL2`` means:
        Index:
            A searchable collection of vectors.
        Flat:
            Exact search. FAISS compares the query vector with every stored
            vector rather than using an approximate-search structure.
        L2:
            Euclidean distance. Smaller distance means vectors are closer and
            therefore treated as more semantically similar.

    Returns:
        LlamaIndex ``FaissVectorStore`` wrapping ``faiss.IndexFlatL2``.

    Flow:
        Embedding vectors
            -> FAISS IndexFlatL2
            -> nearest-vector search
    """
    import faiss
    from llama_index.vector_stores.faiss import FaissVectorStore

    # The FAISS dimension must be exactly the same as the embedding dimension.
    faiss_index = faiss.IndexFlatL2(dimensions)

    # LlamaIndex wraps the raw FAISS index behind its VectorStore interface.
    return FaissVectorStore(faiss_index=faiss_index)
