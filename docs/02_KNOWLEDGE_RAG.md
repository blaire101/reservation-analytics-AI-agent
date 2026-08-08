# Part 2 — Knowledge RAG

![LlamaIndex + FAISS](architecture/03-llamaindex-faiss.png)

## Goal

Answer metric-definition and data-model questions from controlled Markdown knowledge.

## Read in This Order

```text
knowledge/kg_reservation_metrics.md
knowledge/kg_data_model.md
        ↓
app/knowledge/rag.py
```

## Flow

```text
Markdown Knowledge
↓
LlamaIndex
↓
Embeddings
↓
FAISS
↓
Retriever
↓
Grounded Answer
```

`rag.py` loads all `.md` files from `knowledge/`. Local mode uses a deterministic fallback; `LLM_ENABLED=true` activates the complete RAG path.
