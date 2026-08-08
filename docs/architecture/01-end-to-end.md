# End-to-End Architecture

The visual separates three boundaries: request entry, controlled answer paths, and physical data access. LangGraph sits at the decision point. QueryBackend sits directly below the Analytics Tool so backend switching stays outside the agent workflow.
