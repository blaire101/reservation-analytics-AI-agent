"""RAG ingestion: load Markdown knowledge files into LlamaIndex Documents."""

from llama_index.core import SimpleDirectoryReader


def load_documents(path):
    """Load Markdown knowledge files as LlamaIndex ``Document`` objects.

    Args:
        path: Directory containing the knowledge files.

    Returns:
        A list of LlamaIndex ``Document`` objects.

    What is a Document object:
        It is LlamaIndex's standard in-memory representation of a loaded file.
        It contains the document text and metadata such as the source filename.
        LlamaIndex later splits these Documents into smaller chunks/nodes for
        embedding and retrieval.

    Flow:
        .md files
            -> SimpleDirectoryReader
            -> Document objects
            -> chunks/nodes
            -> embeddings
    """
    return SimpleDirectoryReader(
        input_dir=str(path),
        required_exts=['.md'],
    ).load_data()
