from app.analytics.matcher import CandidateMatcher
from app.core.models import EntityCandidate
from app.settings import Settings


def matcher() -> CandidateMatcher:
    return CandidateMatcher(Settings(use_llm=False))


def test_exact_id():
    candidates = [
        EntityCandidate(entity_id="P001", name="Phone Mi 17 Pro"),
        EntityCandidate(entity_id="P002", name="Phone Mi 17"),
    ]
    result = matcher().match("product", "P001", candidates)
    assert result.selected_id == "P001"


def test_normalized_name():
    candidates = [
        EntityCandidate(entity_id="P001", name="Phone Mi 17 Pro"),
        EntityCandidate(entity_id="P002", name="Phone Mi 17"),
    ]
    result = matcher().match("product", "Mi   17 Pro", candidates)
    assert result.selected_id == "P001"


def test_ambiguous_does_not_guess_variant():
    candidates = [
        EntityCandidate(entity_id="P001", name="Phone Mi 17 Pro"),
        EntityCandidate(entity_id="P002", name="Phone Mi 17"),
    ]
    result = matcher().match("product", "Mi 17", candidates)
    assert result.selected_id == "P002"
