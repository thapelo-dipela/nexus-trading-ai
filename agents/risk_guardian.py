"""
RiskGuardianAgent — hard veto triggers and volatility-scaled signal.
"""
import logging
from typing import List, Tuple

import numpy as np

from agents.base import BaseAgent, MarketData, Vote, VoteDirection
import config

logger = logging.getLogger(__name__)


class RiskGuardianAgent(BaseAgent):
    """
    Hard veto triggers (any one is sufficient to override and output HOLD):
    1. prism_risk.risk_score >= PRISM_RISK_VETO_THRESHOLD (default 75)
    2. Portfolio drawdown from peak >= MAX_DRAWDOWN_PCT (default 5%)
    3. Normalised ATR from candles >= VOLATILITY_THRESHOLD (default 4%)
    4. Open position >= MAX_POSITION_PCT of portfolio (default 20%)

    When not vetoing, contribute a mild signal based on PRISM risk proximity to threshold.
    """

    def __init__(self, agent_id: str = "risk_guardian", reasoning: str = "Hard veto triggers and volatility-scaled signal."):
        super().__init__(agent_id, reasoning)
        self.peak_portfolio_value = 0.0

    def analyze(self, market_data: MarketData) -> Vote:
        """Analyze risk and return a vote."""
        component_scores = {}

        # Check all four veto conditions
        veto_reasons: List[str] = []

        # Condition 1: PRISM risk score veto
        # risk_score is computed as: min(100, max_drawdown * 2 + annual_volatility)
        # A score above 75 means extreme conditions
        if market_data.prism_risk and market_data.prism_risk.risk_score >= config.PRISM_RISK_VETO_THRESHOLD:
            logger.debug(
                f"[dim]PRISM risk: score={market_data.prism_risk.risk_score:.1f} "
                f"drawdown={market_data.prism_risk.current_drawdown:.2f}% "
                f"sharpe={market_data.prism_risk.sharpe_ratio:.2f}[/dim]"
            )
            veto_reasons.append(f"PRISM risk_score={market_data.prism_risk.risk_score:.1f} >= {config.PRISM_RISK_VETO_THRESHOLD}")

        # Condition 2: Portfolio drawdown veto
        if self.peak_portfolio_value == 0.0:
            self.peak_portfolio_value = market_data.portfolio_value_usd
        else:
            drawdown = (self.peak_portfolio_value - market_data.portfolio_value_usd) / self.peak_portfolio_value * 100.0
            if drawdown >= config.MAX_DRAWDOWN_PCT:
                veto_reasons.append(f"Drawdown={drawdown:.2f}% >= {config.MAX_DRAWDOWN_PCT}%")

        # Update peak
        self.peak_portfolio_value = max(self.peak_portfolio_value, market_data.portfolio_value_usd)

        # Condition 3: ATR volatility veto
        atr_pct = self._compute_atr_pct(market_data.highs(), market_data.lows(), market_data.closes())
        if atr_pct >= config.VOLATILITY_THRESHOLD:
            veto_reasons.append(f"ATR={atr_pct:.4f} >= {config.VOLATILITY_THRESHOLD}")

        # Condition 4: Open position veto
        position_pct = (market_data.open_position_usd / market_data.portfolio_value_usd * 100.0) if market_data.portfolio_value_usd > 0 else 0.0
        if position_pct >= config.MAX_POSITION_PCT:
            veto_reasons.append(f"Position={position_pct:.1f}% >= {config.MAX_POSITION_PCT}%")

        # If any veto condition triggered, return HOLD
        if veto_reasons:
            veto_msg = " | ".join(veto_reasons)
            logger.warning(f"[yellow]RiskGuardianAgent VETO: {veto_msg}[/yellow]")
            return Vote(
                agent_id=self.agent_id,
                direction=VoteDirection.HOLD,
                confidence=1.0,  # High confidence in veto
                reasoning=f"Risk veto: {veto_msg}",
                component_scores={"veto_triggered": True},
            )

        # No veto — contribute mild signal based on PRISM risk proximity to threshold
        risk_signal = 0.0
        if market_data.prism_risk:
            risk_score = market_data.prism_risk.risk_score
            # Mild negative signal as we approach the veto threshold
            # At 50: risk_signal=+0.2, At 75: risk_signal=-0.2
            risk_signal = (50.0 - risk_score) / 125.0
        else:
            risk_signal = 0.1  # Mild positive default when PRISM risk unavailable

        component_scores["risk_signal"] = risk_signal
        component_scores["atr_pct"] = atr_pct

        logger.debug(f"[dim]RiskGuardianAgent: no veto, risk_signal={risk_signal:.3f}, ATR={atr_pct:.4f}[/dim]")

        # Mild signal; rarely directs trade on its own
        if risk_signal > 0.2:
            direction = VoteDirection.BUY
            confidence = 0.3
        elif risk_signal < -0.2:
            direction = VoteDirection.SELL
            confidence = 0.3
        else:
            direction = VoteDirection.HOLD
            confidence = 0.2

        return Vote(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            reasoning=f"Risk signal: {risk_signal:.3f}",
            component_scores=component_scores,
        )

    @staticmethod
    def _compute_atr_pct(highs: List[float], lows: List[float], closes: List[float]) -> float:
        """
        Compute Average True Range as percentage of current price.
        ATR (14-period default).
        """
        if len(closes) < 14:
            return 0.0

        highs_arr = np.array(highs[-14:])
        lows_arr = np.array(lows[-14:])
        closes_arr = np.array(closes[-14:])

        # True Range = max(H - L, abs(H - C_prev), abs(L - C_prev))
        hl = highs_arr - lows_arr
        hc = np.abs(highs_arr - np.roll(closes_arr, 1))
        lc = np.abs(lows_arr - np.roll(closes_arr, 1))

        tr = np.maximum(hl, np.maximum(hc, lc))
        atr = tr.mean()

        # Normalize to percentage of current price
        current_price = closes[-1]
        if current_price <= 0:
            return 0.0

        atr_pct = atr / current_price
        return atr_pct
