"""Small local demo that runs representative questions through the full agent.

Use this file when you want to see the end-to-end behavior without starting
FastAPI.

Flow:
    load settings
        -> create QueryBackend
        -> create ReservationAgent
        -> invoke example questions
        -> print route / status / answer
"""

from app.analytics.query.backend import create_backend
from app.graph.workflow import ReservationAgent
from app.settings import load_settings


def main() -> None:
    """Run a few knowledge, analytics, and ambiguity examples locally."""
    # 1. Load the local demo configuration.
    settings = load_settings('config/local.env')

    # 2. Create the selected data backend (SQLite by default).
    backend = create_backend(settings)

    # 3. Build the LangGraph agent that uses both RAG and analytics paths.
    agent = ReservationAgent(settings, backend)

    # These examples show the main paths a user can take.
    questions = [
        # Knowledge question -> RAG.
        'What does reserved but not ordered mean?',

        # Analytics question -> validation -> resolution -> controlled SQL.
        'How many users reserved Phone Mi 17 Pro in Germany for CMP001?',

        # Another allowlisted analytics metric.
        'What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?',
    ]

    for question in questions:
        result = agent.invoke(question)
        print(
            f'\nQ: {question}'
            f"\nRoute: {result.get('route')}"
            f"\nStatus: {result.get('status')}"
            f"\nA: {result.get('answer')}"
        )

    # 4. Ambiguity example:
    # Natural-language context may match multiple governed campaigns.
    first = agent.invoke(
        'How many users reserved Phone Mi 17 Pro in Germany in August 2026?'
    )
    print(f"\nQ: ambiguous campaign\nA: {first.get('answer')}")

    # The application returns governed candidates. The user can retry with one
    # stable ID; the second request then uses exact ID validation.
    if first.get('status') == 'clarification' and first.get('candidates'):
        campaign_id = first['candidates'][0]['entity_id']
        second = agent.invoke(
            f'How many users reserved Phone Mi 17 Pro in Germany for {campaign_id}?'
        )
        print(
            f'\nUser retries with: {campaign_id}'
            f"\nA: {second.get('answer')}"
        )


if __name__ == '__main__':
    main()
