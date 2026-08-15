from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


def main() -> None:
    settings = load_settings("config/local.env")
    agent = ReservationAgent(settings, create_backend(settings))

    questions = [
        "What does reserved but not ordered mean?",
        "How many users reserved Phone Mi 17 Pro in Germany for CMP001?",
        "What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?",
    ]
    for question in questions:
        result = agent.invoke(question, session_id="cli-demo")
        print(f"\nQ: {question}\nRoute: {result.get('route')}\nStatus: {result.get('status')}\nA: {result.get('answer')}")

    # Multi-turn clarification example.
    first = agent.invoke(
        "How many users reserved Phone Mi 17 Pro in Germany in August 2026?",
        session_id="clarification-demo",
    )
    print(f"\nQ: ambiguous campaign\nA: {first.get('answer')}")
    if first.get("status") == "clarification":
        second = agent.invoke("CMP001", session_id="clarification-demo")
        print(f"\nUser confirms: CMP001\nA: {second.get('answer')}")


if __name__ == "__main__":
    main()
