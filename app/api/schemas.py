"""Pydantic request and response models used by the FastAPI layer."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Input body accepted by ``POST /ask``.

    Attributes:
        question: Natural-language question from the business user. The field
            must contain at least one character.
    """

    question: str = Field(min_length=1)


class AskResponse(BaseModel):
    """Normalized response returned by ``POST /ask``.

    Attributes:
        answer: Final human-readable answer.
        route: Which path handled the request: ``knowledge`` or ``analytics``.
        status: Current workflow status, for example ``answered`` or
            ``clarification``.
        candidates: Optional governed entity candidates when a name is
            ambiguous.
    """

    answer: str
    route: str
    status: str
    candidates: list[dict] = Field(default_factory=list)
