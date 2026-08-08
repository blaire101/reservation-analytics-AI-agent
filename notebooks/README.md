# Learning Notebooks

Run these notebooks in order. They deliberately expose one concept at a time.

1. `01_structured_output.ipynb` — natural language to Pydantic structure.
2. `02_llamaindex_faiss_rag.ipynb` — knowledge retrieval path.
3. `03_langgraph_routing.ipynb` — state, nodes, edges, and routing.
4. `04_controlled_sql.ipynb` — campaign resolution and metric SQL.
5. `05_end_to_end_agent.ipynb` — connect the complete local path.

## Output Format

Notebook dictionaries and lists are printed with `json.dumps(..., indent=2, ensure_ascii=False)` so structured results are easy to read.
