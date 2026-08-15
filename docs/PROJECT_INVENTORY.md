# Project Inventory

This file is a quick completeness check for the project discussion package.

## Core Application

- `app/core/models.py`
- `app/core/extractor.py`
- `app/core/graph.py`
- `app/analytics/resolver.py`
- `app/analytics/service.py`
- `app/knowledge/rag.py`
- `app/data/backend.py`
- `app/data/sqlite.py`
- `app/data/remote.py`
- `app/main.py`

## Project-Flow Notebooks

1. `notebooks/01_structured_output.ipynb`
2. `notebooks/02_llamaindex_faiss_rag.ipynb`
3. `notebooks/03_langgraph_routing.ipynb`
4. `notebooks/04_controlled_sql.ipynb`
5. `notebooks/05_end_to_end_agent.ipynb`

## Technology Deep-Dive Notebooks

1. `notebooks/pydantic/pydantic_project_learning.ipynb`
2. `notebooks/langchain/langchain_project_learning.ipynb`
3. `notebooks/llamaindex/llamaindex_project_learning.ipynb`
4. `notebooks/faiss/faiss_project_learning.ipynb`
5. `notebooks/langgraph/langgraph_project_learning.ipynb`
6. `notebooks/fastapi/fastapi_project_learning.ipynb`

## Presentation / Learning Material

- `presentation/reservation_ai_learning_v836.html`
- `presentation/reservation_analytics_ai_agent_7slides_v11_clean.pptx`

## Configuration

- `.env.example`
- `.gitignore`
- `config/local.env`
- `config/aws.env`
- `config/internal.env`

## Validation

- Markdown image references checked: no missing local images.
- All 11 notebooks validated as notebook JSON and executed successfully in the local environment.
- `pytest`: 8 tests passed.
