#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agent_service import ReservationAgentService
from app.config import AppSettings


DEFAULT_QUESTIONS = [
    "What does reserved-but-not-ordered mean?",
    "How is reservation-to-order conversion rate calculated?",
    "How many users reserved Xiaomi 17 Pro in Germany for CMP001 but did not order?",
    "How many users reserved Xiaomi 17 Pro?",
    "Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--question")
    parser.add_argument("--session-id", default="demo")
    args = parser.parse_args()

    settings = AppSettings(mock_mode=True)
    service = ReservationAgentService(settings)

    questions = [args.question] if args.question else DEFAULT_QUESTIONS

    for q in questions:
        print("=" * 88)
        print("USER:", q)
        r = service.chat(q, args.session_id)
        print("ROUTE:", r.route)
        print("STATUS:", r.status)
        print("PARAMS:", r.extracted.model_dump() if r.extracted else None)
        print("ANSWER:")
        print(r.answer)
        print()

    if not args.question:
        print("=" * 88)
        print("FOLLOW-UP DEMO")
        session = "ambiguous-demo"
        first = service.chat(
            "Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.",
            session,
        )
        print("USER: Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.")
        print(first.answer)
        second = service.chat("CMP001", session)
        print("\nUSER: CMP001")
        print(second.answer)


if __name__ == "__main__":
    main()
