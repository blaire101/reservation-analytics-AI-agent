"""Typed shared state passed between LangGraph nodes."""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Represent the data carried through the LangGraph workflow.

    LangGraph nodes read fields from this dictionary and return updated fields.
    ``total=False`` means a field does not need to exist at every workflow step.

    Main lifecycle:
        question
            -> intent / metric / query
            -> validation status
            -> resolved_context
            -> answer
    """

    # Original user input.
    question: str

    # Structured output created by the extraction node.
    intent: str
    metric: str
    detail_requested: bool
    query: dict

    # Workflow metadata.
    route: str
    status: str

    # Final or clarification response.
    answer: str

    # Stable governed IDs after entity resolution.
    resolved_context: dict

    # Candidate entities returned when a name is ambiguous.
    candidates: list[dict]
