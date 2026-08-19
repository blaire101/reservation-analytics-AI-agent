# Project Story

The operations team had two needs: trusted recurring metrics and flexible ad-hoc questions.

I first built a governed Reservation Data Mart. Then I added an AI Agent with two controlled paths:

- **Knowledge path:** RAG explains definitions and metric rules.
- **Analytics path:** LLM extracts a business plan, stable IDs are validated directly, names are resolved only when needed, and application code runs controlled SQL.

The design avoids two risks: the LLM does not invent warehouse IDs and does not freely generate analytics SQL.
