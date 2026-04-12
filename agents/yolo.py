"""
YOLOAgent — Extreme bullish consensus activation.
Source: Ice-cream repo contribution for max-aggression trading mode.
Activates only under extreme bullish convergence (all agents agree + greed + low risk).
"""

import logging
from typing import List, Optional
from .base import BaseAgent, MarketData, Vote

logger = logging.getLogger("nexus")


class YOLOAgent(BaseAgent):
    """
    Special high-conviction agent that activates only when ALL conditions align.
    Uses maximum position size ($500), shortest hold time, highest confidence.
    
    ACTIVATION REQUIREMENTS (all must be true simultaneously):
      - Fear/Greed Index >= 75 (greed zone)
      - All non-risk-guardian agents vote BUY
      - CVD momentum >= 0.20 (institutional buying confirmed)
      - Price above VWAP
      - PRISM risk score <= 60
      - Current drawdown <= 3%
      
    Safety Rules (hard-enforced):
      - Never activate if drawdown >= 3%
      - After hitting SL: 1 hour cooldown before reactivation
      - Max 3 activations per 24 hours
      - Logs all activations to cycle log with "yolo": true flag
    """

    ACTIVATION_REQUIREMENTS = {
        "fear_greed_min": 75,
        "cvd_momentum_min": 0.20,
        "price_above_vwap": True,
        "prism_risk_max": 60,
        "drawdown_max_pct": 3.0,
        "all_agents_direction": "BUY",
    }

    def __init__(self):
        super().__init__("yolo")
        self.weight = 1.5  # between standard agents (1.0) and LLM (2.0)
        self._activated: bool = False
        self._activation_count: int = 0
        self._last_activation_timestamp: int = 0
        self._cooldown_until_timestamp: int = 0
        self._activations_24h: List[int] = []  # timestamps of activations in last 24h

    def is_activation_condition_met(
        self,
        market: MarketData,
        prior_votes: List[Vote],
    ) -> bool:
        """
        Returns True only if every activation requirement is satisfied.
        Called before vote() to decide if YOLO should fire.
        
        Args:
            market: Current market data with all signals
            prior_votes: Votes from standard agents (orderflow, momentum, sentiment, risk_guardian)
            
        Returns:
            bool: True if all conditions met, False otherwise
        """
        import time

        reqs = self.ACTIVATION_REQUIREMENTS

        # 1. Fear/Greed must be in greed zone
        if (market.fear_greed or 0) < reqs["fear_greed_min"]:
            logger.debug(
                f"YOLO: Fear/Greed {market.fear_greed} < {reqs['fear_greed_min']} — not greedy enough"
            )
            return False

        # 2. Current drawdown must be within limit
        if market.current_drawdown_pct > reqs["drawdown_max_pct"]:
            logger.warning(
                f"YOLO: Drawdown {market.current_drawdown_pct:.2f}% > "
                f"{reqs['drawdown_max_pct']}% — too risky"
            )
            return False

        # 3. PRISM risk score must be acceptable
        if (
            market.prism_risk
            and market.prism_risk.risk_score > reqs["prism_risk_max"]
        ):
            logger.debug(
                f"YOLO: Risk score {market.prism_risk.risk_score} > "
                f"{reqs['prism_risk_max']} — too risky"
            )
            return False

        # 4. CVD momentum must show institutional buying
        cvd = getattr(market, "cvd", None)
        if cvd is None or cvd < reqs["cvd_momentum_min"]:
            logger.debug(
                f"YOLO: CVD {cvd} < {reqs['cvd_momentum_min']} — no institutional buying"
            )
            return False

        # 5. Price must be above VWAP
        vwap = getattr(market, "vwap", None)
        if vwap and market.price < vwap:
            logger.debug(f"YOLO: Price {market.price} < VWAP {vwap} — bearish divergence")
            return False

        # 6. Check cooldown from previous SL hit
        now = int(time.time())
        if now < self._cooldown_until_timestamp:
            cooldown_remaining = self._cooldown_until_timestamp - now
            logger.debug(f"YOLO: Still in cooldown for {cooldown_remaining}s")
            return False

        # 7. Check max 3 activations per 24h
        cutoff = now - 86400  # 24h ago
        self._activations_24h = [ts for ts in self._activations_24h if ts > cutoff]
        if len(self._activations_24h) >= 3:
            logger.warning(
                f"YOLO: Already activated 3 times in 24h — rate limited"
            )
            return False

        # 8. All non-risk-guardian agents must vote BUY
        # (RiskGuardian can veto without blocking YOLO)
        non_veto_votes = [
            v for v in prior_votes if v.agent_id != "risk_guardian"
        ]
        if not all(v.direction == "BUY" for v in non_veto_votes):
            agents_not_buy = [
                v.agent_id for v in non_veto_votes if v.direction != "BUY"
            ]
            logger.debug(
                f"YOLO: Not all agents agree BUY — {agents_not_buy} disagree"
            )
            return False

        logger.warning("✓ YOLO ACTIVATION CONDITIONS MET")
        return True

    def analyze(self, market: MarketData) -> Vote:
        """
        Only called when is_activation_condition_met() returns True.
        Returns max-confidence BUY vote.
        """
        import time

        self._activated = True
        self._activation_count += 1
        now = int(time.time())
        self._last_activation_timestamp = now
        self._activations_24h.append(now)

        reasoning = (
            f"YOLO ACTIVATED (#{self._activation_count}) | "
            f"FG={market.fear_greed} | "
            f"CVD={getattr(market, 'cvd', 0):.3f} | "
            f"Risk={market.prism_risk.risk_score if market.prism_risk else 'N/A'} | "
            f"All agents aligned BUY — maximum aggression mode"
        )

        logger.warning(f"⚡ {reasoning}")

        return Vote(
            agent_id=self.agent_id,
            direction="BUY",
            confidence=0.95,
            reasoning=reasoning,
        )

    def deactivate(self) -> None:
        """Called when YOLO position hits stop-loss."""
        import time

        self._activated = False
        now = int(time.time())
        self._cooldown_until_timestamp = now + 3600  # 1 hour cooldown
        logger.warning(
            f"YOLO: Position SL hit — entering 1h cooldown until "
            f"{self._cooldown_until_timestamp}"
        )

    def is_active(self) -> bool:
        """Returns whether YOLO is currently in an active trade."""
        return self._activated
