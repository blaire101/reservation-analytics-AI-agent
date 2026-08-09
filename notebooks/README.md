# Learning Notebooks

Run these notebooks in order. They deliberately expose one concept at a time.

1. `01_structured_output.ipynb` — natural language to Pydantic structure.
2. `02_llamaindex_faiss_rag.ipynb` — knowledge retrieval path.
3. `03_langgraph_routing.ipynb` — state, nodes, edges, and routing.
4. `04_controlled_sql.ipynb` — campaign resolution and metric SQL.
5. `05_end_to_end_agent.ipynb` — connect the complete local path.

## Output Format

Notebook dictionaries and lists are printed with `json.dumps(..., indent=2, ensure_ascii=False)` so structured results are easy to read.


# Reservation Analytics AI Agent — Notebook Learning Center

This folder contains two complementary learning tracks:

## Track A — Project Flow

These notebooks teach the project in execution order:

```text
01_structured_output.ipynb
        ↓
02_llamaindex_faiss_rag.ipynb
        ↓
03_langgraph_routing.ipynb
        ↓
04_controlled_sql.ipynb
        ↓
05_end_to_end_agent.ipynb
```

## Track B — Technology Deep Dives

Each major technology has its own directory:

```text
notebooks/
├── pydantic/
│   └── pydantic_project_learning.ipynb
├── langchain/
│   └── langchain_project_learning.ipynb
├── llamaindex/
│   └── llamaindex_project_learning.ipynb
├── faiss/
│   └── faiss_project_learning.ipynb
├── langgraph/
│   └── 03_langgraph_routing.ipynb
└── fastapi/
    └── fastapi_project_learning.ipynb
```

Every directory also contains a detailed `README.md` explaining:

- the technology;
- the mental model;
- core concepts;
- important APIs;
- diagrams;
- code examples;
- where the technology is used in this project;
- what the project does not use;
- production improvements;
- Q&A.

---

# Recommended Learning Order

For understanding the project from first principles:

```text
1. Pydantic
      ↓
2. LangChain Structured Output
      ↓
3. LlamaIndex
      ↓
4. FAISS
      ↓
5. LangGraph
      ↓
6. Controlled SQL
      ↓
7. FastAPI
      ↓
8. End-to-End Agent
```

Why:

1. **Pydantic** defines the contracts.
2. **LangChain / ChatOpenAI** fills the structured extraction contract.
3. **LlamaIndex** organizes the RAG layer.
4. **FAISS** explains the vector retrieval under RAG.
5. **LangGraph** connects the paths with state and routing.
6. **Controlled SQL** explains trusted numeric analytics.
7. **FastAPI** exposes the finished workflow through HTTP.
8. **End-to-End** brings everything together.

---

# Architecture Responsibilities

```text
Natural-language question
        ↓
FastAPI
        ↓
LangChain / ChatOpenAI
Structured Output
        ↓
Pydantic
Typed Contract
        ↓
LangGraph
State + Routing
      ↙       ↘
Knowledge   Analytics
   ↓           ↓
LlamaIndex   Resolver
   ↓           ↓
FAISS       Controlled SQL
      ↘       ↙
       Answer
```

---

# Does the Project Use LangChain?

**Yes, but only for a focused responsibility.**

Current code uses:

```python
from langchain_openai import ChatOpenAI

ChatOpenAI(...).with_structured_output(
    ExtractedRequest
)
```

So LangChain's OpenAI integration is used for **structured extraction**.

The project does not use LangChain as the single top-level framework because:

- LangGraph owns workflow orchestration;
- LlamaIndex owns RAG;
- FAISS owns vector search;
- Pydantic owns typed contracts;
- Python controls SQL;
- FastAPI owns HTTP serving.

This is intentional separation of concerns.

---

# What You Should Be Able to Explain After Studying

After completing both tracks, you should be able to explain the project from two perspectives.

## Perspective 1 — Technology

```text
What is Pydantic?
What is LangChain?
What is LlamaIndex?
What is FAISS?
What is LangGraph?
What is FastAPI?
```

## Perspective 2 — Runtime

```text
What happens when the user asks a question?
How is the intent extracted?
How is the data validated?
How does the graph route the request?
How does RAG retrieve knowledge?
How is a campaign resolved?
How is SQL controlled?
How does FastAPI return the answer?
```

---

# Important Boundary

These notebooks give you:

- strong fundamentals;
- the core APIs used by the project;
- the project-specific implementation;
- the main architecture decisions;
- common Q&A.

They do **not** make you an expert in every feature of each framework.

For example, advanced topics that are intentionally outside the current project include:

- distributed / persistent vector databases;
- advanced LangGraph multi-agent subgraphs;
- complex LangChain agent tool ecosystems;
- full async FastAPI production architecture;
- high-scale authentication/rate limiting;
- advanced LlamaIndex reranking and hybrid retrieval.

That is okay.

The goal is:

> Understand the fundamentals deeply enough to explain and modify this project confidently.


---

## Classic Architecture Answer

A concise answer to memorize:

> I use LangChain selectively rather than making it the entire application framework. LangChain's ChatOpenAI integration handles structured extraction, LangGraph handles stateful workflow orchestration, and LlamaIndex with FAISS handles the knowledge RAG layer. This keeps responsibilities explicit and prevents the LLM from directly controlling analytics SQL.

