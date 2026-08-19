# Start Here

Use the materials in this order.

## 1. README.md - Understand the Project
Read these sections first:

```text
Core Flow
    ↓
RAG Flow
    ↓
Analytics Flow
    ↓
Application Structure
    ↓
Example Walkthroughs
```

Goal: understand the complete system in 10 minutes.

## 2. presentation/reservation_ai_learning_final.html - Learn the Details
The HTML guide uses the same vocabulary as the README and code.

Tabs:

```text
Overview
Data Mart
RAG
Analytics
Examples
Code Structure
Production
Quick Review
```

Goal: understand unfamiliar terms such as Document objects, embeddings, 1536 dimensions, IndexFlatL2, Top-K, entity resolution, and controlled SQL.

## 3. presentation/reservation_analytics_ai_agent_8slides_clear_final.pptx - Practice the Project Story
Slides:

```text
1. Business Problem & Goal
2. Trusted Reservation Data Mart
3. Core Flow
4. RAG Flow
5. Analytics Flow
6. Example Walkthroughs
7. Application Structure
8. Production Design & Safety Boundaries
```

Speaker notes are embedded in every slide. A separate copy is also available in `presentation/speaker_notes_final.md`.

## 4. Read the Code

```text
1. app/graph/workflow.py
2. app/graph/nodes/extract.py
3. app/rag/service.py
4. app/rag/*
5. app/analytics/resolution/
6. app/analytics/metrics/
7. app/analytics/service.py
```

Every application module, class, and function contains a docstring.

## One Sentence to Remember

> LangGraph routes the request. RAG answers knowledge questions. Analytics returns trusted business numbers through controlled SQL.
