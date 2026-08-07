from __future__ import annotations

import unittest

from app.agent_service import ReservationAgentService
from app.config import AppSettings


class ReservationAgentLocalSQLTests(unittest.TestCase):
    def setUp(self):
        self.service = ReservationAgentService(
            AppSettings(mock_mode=True, data_backend="sqlite", local_seed_on_start=True)
        )

    def test_backend_is_real_local_sql(self):
        self.assertEqual(self.service.backend.name, "sqlite")
        rows = self.service.backend.execute(
            "SELECT COUNT(*) AS n FROM reservation_dm.dm_reservation_conversion",
            database="reservation_dm",
        )
        self.assertGreater(int(rows[0]["n"]), 0)

    def test_knowledge(self):
        r = self.service.chat("What does reserved-but-not-ordered mean?", "t1")
        self.assertEqual(r.status, "answered")
        self.assertIn("llamaindex", r.route.lower())
        self.assertIn("no corresponding order", r.answer)

    def test_exact_campaign_analytics(self):
        r = self.service.chat(
            "How many users reserved Xiaomi 17 Pro in Germany for CMP001 but did not order?",
            "t2",
        )
        self.assertEqual(r.status, "answered")
        self.assertEqual(r.resolved_campaign.campaign_id, "CMP001")
        self.assertIn("3 users", r.answer)
        self.assertIn("sqlite", r.route.lower())

    def test_missing_parameters(self):
        r = self.service.chat("How many users reserved Xiaomi 17 Pro?", "t3")
        self.assertEqual(r.status, "clarification")
        self.assertIn("country or site", r.answer)
        self.assertIn("campaign", r.answer)

    def test_ambiguous_campaign_then_followup(self):
        sid = "t4"
        r1 = self.service.chat(
            "Analyze the Xiaomi 17 Pro campaign in Germany in August 2026.", sid
        )
        self.assertEqual(r1.status, "clarification")
        self.assertIn("CMP001", r1.answer)
        self.assertIn("CMP002", r1.answer)
        self.assertIn("CMP003", r1.answer)

        r2 = self.service.chat("CMP001", sid)
        self.assertEqual(r2.status, "answered")
        self.assertIn("62.50%", r2.answer)


if __name__ == "__main__":
    unittest.main()
