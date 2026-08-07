# Runtime Request Flow

The runtime does not send every question directly to SQL.

- Knowledge questions go to LlamaIndex RAG.
- Analytics questions must pass validation and campaign resolution.
- Missing or ambiguous context produces clarification rather than a guessed answer.
- SQL runs only after one `campaign_id` has been resolved.
