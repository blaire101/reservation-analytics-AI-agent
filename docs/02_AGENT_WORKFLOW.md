# Part 2 — Agent Workflow

## 1. Runtime flow

![Runtime Request Flow](architecture/architecture-request-flow.png)

The important modules are:

```text
app/agent_service.py
        ↓
app/graph.py
        ↓
extractor.py
        ↓
route: knowledge or analytics
```

## 2. Structured extraction

Natural language is converted into a small business context rather than directly into SQL.

Typical fields:

```python
country
site
product
campaign_id
campaign_name
campaign_month
campaign_year
user_id
```

Missing required context is not guessed.

## 3. Knowledge path

```text
User question
   ↓
LangGraph route = knowledge
   ↓
LlamaIndex
   ↓
knowledge/reservation_analytics.md
   ↓
Grounded answer
```

Use this for questions such as:

- What does reserved-but-not-ordered mean?
- How is conversion rate calculated?
- What is the Data Mart grain?

## 4. Analytics path

```text
User question
   ↓
Structured context
   ↓
Validation
   ↓
Campaign Resolver
   ↓
Exactly one campaign_id
   ↓
Analytics Tool
   ↓
Controlled SQL template
   ↓
QueryBackend
```

The application, not the LLM, owns the SQL templates.

## 5. Campaign resolution

A phrase like *the August Xiaomi 17 Pro campaign in Germany* can match more than one campaign.

Resolution rules:

- 0 matches → tell the user no campaign was found.
- 1 match → continue.
- multiple matches → return candidates and request clarification.

The analytics query proceeds only when one `campaign_id` has been resolved.

## 6. State and follow-up

LangGraph keeps enough state to merge a short follow-up with the previous request. For example, after listing several candidates, the user can answer only `CMP001` and the workflow can reuse the existing country/product context.

## 7. Key source files

| File | Purpose |
|---|---|
| `app/graph.py` | routing and workflow state |
| `app/services/extractor.py` | structured business context |
| `app/services/knowledge.py` | LlamaIndex RAG |
| `app/services/campaign_resolver.py` | unique campaign resolution |
| `app/services/analytics.py` | controlled SQL templates |
