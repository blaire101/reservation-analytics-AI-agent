# Project Story — Reservation Analytics AI Agent

## 30-second summary

I first built a trusted Reservation Data Mart for campaign analytics. Then I added a controlled natural-language layer with two answer paths: LlamaIndex + FAISS RAG for business definitions, and application-controlled SQL for actual business numbers. For analytics questions, the LLM only extracts natural-language context. The application resolves multilingual country, product, and campaign wording against governed dimensions, asks the user to confirm ambiguous candidates, keeps that clarification state by session ID, and only then runs predefined SQL against the Data Mart.

## 2-minute architecture story

1. **Trusted data foundation** — `dm_reservation_subject_df` is the source of truth at User × Campaign × Product × Country grain.
2. **Structured extraction** — Pydantic converts English, Chinese, or mixed-language questions into typed intent, metric, and business context.
3. **Two paths** — Knowledge questions go to RAG; analytics questions go to validation and entity resolution.
4. **Governed entity resolution** — Country, product, and campaign candidates come from dimension tables. The LLM may compare meaning, but can select only returned IDs.
5. **Clarification loop** — If several candidates are plausible, the agent asks the user and stores the pending candidates and previous context by `session_id`.
6. **Controlled execution** — `AnalyticsService` owns metric logic, `QueryBackend` executes SQL, and the Data Mart returns trusted numbers.
7. **Serving** — FastAPI exposes the agent; the application can be packaged as one Docker image and deployed as Kubernetes pods. Production conversation state should use a durable checkpoint store for multi-pod resume.

## Strong project discussion sentence

> I do not let the LLM invent warehouse IDs or freely generate analytics SQL. I use it for semantic understanding, ground entities in governed dimensions, clarify ambiguity with stateful memory, and let application code control the final query.

## Prototype vs production

**Implemented in the prototype:** structured extraction, RAG, dimension-backed resolution, conservative candidate selection, clarification by `session_id`, controlled SQL, backend abstraction, FastAPI.

**Production hardening:** durable distributed conversation state, parameterized queries where supported, scalable entity candidate search for very large dimensions, authentication/authorization, audit logging, rate limits, and observability.
