"""RAG embeddings: convert knowledge chunks and queries into numeric vectors."""

from llama_index.embeddings.openai import OpenAIEmbedding


def build_embedding(settings):
    """Create the embedding model used by both indexing and retrieval.

    Args:
        settings: Application settings containing embedding model name and API
            key.

    Returns:
        LlamaIndex ``OpenAIEmbedding`` instance.

    Why the same model is used twice:
        During indexing, document chunks become vectors.
        During retrieval, the user question becomes a vector.
        Because both use the same embedding model, FAISS can compare them in
        the same vector space.

    Flow:
        Text chunk -> embedding model -> vector
        User query -> embedding model -> vector
    """
    return OpenAIEmbedding(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )
