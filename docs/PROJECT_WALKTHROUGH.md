# Project Preparation

## 30-second project answer

I built a reservation analytics data mart on AWS using S3, Glue, the Glue Data Catalog, and Athena.

The data mart combines reservation and order data at the user, campaign, product, and site grain.

On top of that existing data mart, I built a small AI prototype for operations users. I used LlamaIndex for business and metric knowledge retrieval, and an analytics tool for actual Athena queries.

Before querying data, I extracted and validated the country, product, and campaign. If the campaign was ambiguous, the agent asked the user to clarify instead of guessing. LangGraph routed requests to either the knowledge path or the analytics path.

## Q1. Why LlamaIndex?

LlamaIndex is used as a higher-level knowledge retrieval layer for business definitions, metric definitions, Data Mart documentation, and campaign rules.

It does not calculate the actual business numbers.

## Q2. What does Athena do?

Athena queries the existing Reservation Analytics DM for actual data.

The simplest distinction is:

**LlamaIndex answers what it means. Athena answers what the actual number is.**

## Q3. Why not let the LLM generate SQL?

I keep analytical SQL behind a controlled tool with fixed query templates.

The LLM extracts business context, but the application validates it, resolves a unique campaign ID, and then executes an allowlisted SQL pattern.

This reduces ambiguity and SQL-injection risk and keeps metric logic governed.

## Q4. Why resolve campaign_id first?

Campaign names and month descriptions are not guaranteed to be unique.

A phrase such as "the August campaign" can match several campaigns.

I query the campaign dimension first. If there is exactly one match, I use its campaign_id. If there are multiple matches, I ask the user to choose.

## Q5. What if the user says only "How many users reserved Xiaomi 17 Pro?"

Country/site and campaign context are missing.

The agent asks for clarification instead of guessing.

## Q6. Analysis date vs campaign date?

They are different.

For post-campaign analysis, the user may ask the question after the campaign has ended. I use the resolved campaign window and campaign ID to filter business data, not the date when the question is asked.

## Q7. What does LangGraph do?

LangGraph handles workflow and routing.

The prototype has only two main routes:

- knowledge -> LlamaIndex
- analytics -> validation -> campaign resolution -> Athena

I intentionally kept the graph small so the control flow is easy to understand and operate.

## Q8. LangChain + FAISS vs LlamaIndex?

In my previous LangChain demo, I built the RAG pipeline more explicitly with document loading, chunking, embeddings, FAISS, and an agent tool.

In this project, I use LlamaIndex as a higher-level knowledge layer for business definitions, metrics, and Data Mart documentation.

## Q9. Who implemented Feishu?

I designed and developed the backend agent service.

Another engineer handled deployment and Feishu integration.

The Feishu bot calls my backend API and displays the response to the operations user.

## Q10. What is the most important design idea?

RAG is for knowledge. SQL is for data.

I do not use vector retrieval to answer actual counts, and I do not query Athena to explain business definitions.

## Whiteboard flow

```text
Natural Language
      ↓
Extract Business Context
      ↓
Country + Product + Campaign
      ↓
Validate / Clarify
      ↓
LangGraph
 ↙             ↘
LlamaIndex    Analytics Tool
 ↓                ↓
Knowledge        Athena
                  ↓
             Existing DM
```
