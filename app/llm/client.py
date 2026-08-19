"""Shared helper for creating deterministic structured-output LLM clients."""

from __future__ import annotations

from app.settings import Settings


def structured_llm(settings: Settings, schema):
    """Create an LLM client that must return a specific Pydantic schema.

    Args:
        settings: Application settings containing model name and API key.
        schema: Pydantic model describing the exact structured output expected
            from the LLM.

    Returns:
        A LangChain ``ChatOpenAI`` runnable configured with structured output.

    Why structured output:
        Instead of asking the LLM to return free text, the application asks it
        to fill a typed business object such as ``ExtractedRequest``. This
        makes routing and downstream validation much safer and easier to test.

    Flow:
        User text
            -> ChatOpenAI
            -> schema validation
            -> typed Python object
    """
    # Fail clearly if the application has no configured LLM credentials.
    settings.require_llm()

    from langchain_openai import ChatOpenAI

    # temperature=0 keeps extraction as deterministic as practical.
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0,
    )

    # with_structured_output() makes the model return data matching ``schema``.
    return llm.with_structured_output(schema)
