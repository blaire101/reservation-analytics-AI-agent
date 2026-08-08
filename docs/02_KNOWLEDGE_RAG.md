# Part 2 — Knowledge RAG

![LlamaIndex + FAISS](architecture/03-llamaindex-faiss.png)

## Goal

Answer business-definition and metric-rule questions from a controlled knowledge source.

## Read in This Order

```text
knowledge/reservation_analytics.md
      ↓
app/knowledge/rag.py
```

## Real RAG Path

```text
Markdown
↓
LlamaIndex
↓
Embeddings
↓
FAISS
↓
Retriever
↓
LLM
↓
Grounded Answer
```

The default local mode uses a deterministic fallback so the repository can run without an API key. Setting `USE_LLM=true` activates the LlamaIndex + FAISS + LLM path.

## Boundary

RAG explains definitions and metadata. It does not return trusted business counts from the Data Mart.
