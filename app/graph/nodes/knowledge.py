"""Knowledge node: answer definitions and rules with the RAG service."""


def run(rag, state):
    """Send the original question to the RAG knowledge path.

    Args:
        rag: ``KnowledgeRAG`` service.
        state: Current LangGraph state containing ``question``.

    Returns:
        Updated state marked as a knowledge answer.

    Flow:
        question -> KnowledgeRAG.answer() -> grounded answer
    """
    answer = rag.answer(state['question'])

    return {
        **state,
        'route': 'knowledge',
        'status': 'answered',
        'answer': answer,
    }
