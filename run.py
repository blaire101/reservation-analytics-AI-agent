from app.core.graph import ReservationAgent
from app.data.backend import create_backend
from app.settings import load_settings


QUESTIONS = [
    "What does reserved but not ordered mean?",
    "How many users reserved Phone Mi 17 Pro in Germany for CMP001?",
    "What was the conversion rate for Phone Mi 17 Pro in Germany for CMP001?",
]


def main() -> None:
    settings = load_settings("config/local.env")
    agent = ReservationAgent(settings, create_backend(settings))

    for question in QUESTIONS:
        result = agent.invoke(question)
        print(f"\nQ: {question}\nRoute: {result.get('route')}\nA: {result.get('answer')}")


if __name__ == "__main__":
    main()
