from dataclasses import dataclass

KNOWN_BAD_IPS: set[str] = set()
KNOWN_BAD_ASNS: set[int] = set()
HIGH_RISK_COUNTRIES: set[str] = set()


@dataclass
class RiskAssessment:
    score: float
    factors: list[str]
    requires_step_up: bool = False
    requires_denial: bool = False


class RiskScorer:
    def assess(
        self,
        ip_address: str,
        user_agent: str,
        asn: int | None = None,
        country: str | None = None,
    ) -> RiskAssessment:
        score = 0.0
        factors: list[str] = []

        if ip_address in KNOWN_BAD_IPS:
            score += 0.5
            factors.append("known_bad_ip")

        if asn and asn in KNOWN_BAD_ASNS:
            score += 0.3
            factors.append("known_bad_asn")

        if country and country in HIGH_RISK_COUNTRIES:
            score += 0.2
            factors.append("high_risk_country")

        if not user_agent or len(user_agent) < 10:
            score += 0.2
            factors.append("missing_user_agent")

        return RiskAssessment(
            score=min(score, 1.0),
            factors=factors,
            requires_step_up=score >= 0.3,
            requires_denial=score >= 0.8,
        )
