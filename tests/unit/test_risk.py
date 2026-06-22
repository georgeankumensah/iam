from django.test import TestCase

from core.risk import RiskScorer


class RiskScorerTests(TestCase):
    def setUp(self) -> None:
        self.scorer = RiskScorer()

    def test_low_risk(self) -> None:
        result = self.scorer.assess(
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 (Macintosh) Chrome/120",
        )
        self.assertLess(result.score, 0.3)
        self.assertFalse(result.requires_step_up)
        self.assertFalse(result.requires_denial)

    def test_missing_user_agent_increases_risk(self) -> None:
        result = self.scorer.assess(ip_address="192.168.1.1", user_agent="")
        self.assertGreaterEqual(result.score, 0.2)

    def test_score_bounded(self) -> None:
        result = self.scorer.assess(ip_address="192.168.1.1", user_agent="UA")
        self.assertLessEqual(result.score, 1.0)
