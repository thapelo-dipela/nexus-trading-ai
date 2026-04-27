"""
OrderFlowAgent — Microstructure Alpha from Order Flow Indicators
Source: uniteonline/OrderFlow-Indicator-AI-Trading
Contributes: CVD momentum, VWAP deviation, bid/ask imbalance detection

This agent reads institutional order flow signals (Cumulative Volume Delta,
Volume-Weighted Average Price, bid/ask imbalance) that pure price-based
indicators cannot detect. It identifies accumulation/distribution divergences.
"""

import logging
from typing import List, Optional
from dataclasses import dataclass
import config
from agents.base import BaseAgent, Vote, VoteDirection, MarketData

logger = logging.getLogger(__name__)


class OrderFlowAgent(BaseAgent):
    """
    Microstructure-based trading agent that detects institutional buying/selling
    pressure via CVD momentum and VWAP divergence analysis.
    """

    def __init__(self):
        super().__init__("orderflow", reasoning="OrderFlow microstructure analysis")
        self.weight = 1.0
        self.consecutive_wrong = 0
        self._cvd_history: List[float] = []  # rolling 30-bar CVD
        self._vwap: float = 0.0
        self._cvd_lookback = config.CVD_LOOKBACK_BARS  # default 30
        self._veto_threshold = config.CVD_VETO_THRESHOLD  # default 0.15 (too strict, reduce to 0.20)
        self._divergence_pct = config.VWAP_DIVERGENCE_PCT  # default 1.0

    def _compute_cvd(self, candles) -> float:
        """
        Compute Cumulative Volume Delta.
        CVD = sum of (volume * sign(close - open)) for each candle.
        Positive = accumulation (buying), negative = distribution (selling).
        """
        if not candles or len(candles) < 1:
            return 0.0

        cvd = 0.0
        for candle in candles:
            price_change = candle.close - candle.open
            sign = 1.0 if price_change > 0 else (-1.0 if price_change < 0 else 0.0)
            cvd += candle.volume * sign

        return cvd

    def _compute_cvd_momentum(self, cvd_now: float) -> float:
        """
        Compute CVD momentum: (cvd_now - cvd_30_bars_ago) / abs(cvd_30_bars_ago).
        Positive and rising = buy pressure.
        Negative and falling = sell pressure.
        """
        if not self._cvd_history or len(self._cvd_history) < self._cvd_lookback:
            return 0.0

        cvd_old = self._cvd_history[0] if self._cvd_history else cvd_now
        if abs(cvd_old) < 1e-9:  # avoid division by zero
            return 0.0

        momentum = (cvd_now - cvd_old) / abs(cvd_old)
        return momentum

    def _compute_vwap(self, candles) -> float:
        """
        Compute Volume-Weighted Average Price.
        VWAP = sum(price * volume) / sum(volume)

        Fallback: if volumes unavailable, use simple average.
        """
        if not candles or len(candles) < 5:
            return 0.0

        total_volume = sum(c.volume for c in candles)
        if total_volume < 1e-9:
            # No volume data, fallback to price average
            return sum(c.close for c in candles) / len(candles)

        numerator = sum(c.close * c.volume for c in candles)
        vwap = numerator / total_volume
        return vwap

    def _compute_bid_ask_imbalance_proxy(self, change_24h_pct: float, cvd_momentum: float) -> float:
        """
        Proxy for bid/ask imbalance using price change and CVD momentum.
        Returns -1.0 (all sells) to +1.0 (all buys).

        Logic:
          - If price up >3% on falling CVD → distribution (bearish)
          - If price down >3% on rising CVD → accumulation (bullish)
          - Otherwise, neutral
        """
        imbalance = 0.0

        if change_24h_pct > 3.0 and cvd_momentum < -0.1:
            # Distribution: price rising but CVD falling
            imbalance = -0.7

        elif change_24h_pct < -3.0 and cvd_momentum > 0.1:
            # Accumulation: price falling but CVD rising
            imbalance = 0.7

        elif change_24h_pct > 1.0:
            imbalance = 0.3

        elif change_24h_pct < -1.0:
            imbalance = -0.3

        return max(-1.0, min(1.0, imbalance))

    def analyze(self, market: MarketData) -> Vote:
        """
        Analyze order flow microstructure and return a vote.

        Step 1: Compute CVD momentum
        Step 2: Compute VWAP deviation
        Step 3: Compute bid/ask imbalance proxy
        Step 4: Hard veto rule (CVD divergence)
        Step 5: Composite signal
        """

        # Get candles (fallback to empty if not available)
        candles = market.candles if market.candles else []

        # Step 1: Compute CVD momentum
        cvd_now = self._compute_cvd(candles)
        self._cvd_history.append(cvd_now)
        # Keep history to lookback size
        if len(self._cvd_history) > self._cvd_lookback:
            self._cvd_history.pop(0)

        cvd_momentum = self._compute_cvd_momentum(cvd_now)

        # Step 2: Compute VWAP deviation
        self._vwap = self._compute_vwap(candles)
        vwap_deviation = 0.0
        if self._vwap > 1e-9:
            vwap_deviation = ((market.current_price - self._vwap) / self._vwap) * 100

        # Step 3: Bid/ask imbalance proxy
        imbalance = self._compute_bid_ask_imbalance_proxy(
            market.change_24h_pct, cvd_momentum
        )

        # Step 4: HARD VETO RULE (non-negotiable)
        # If cvd_momentum < -0.15 AND price > vwap → distribution veto
        if cvd_momentum < -self._veto_threshold and market.current_price > self._vwap:
            reasoning = (
                f"CVD divergence VETO: cvd_momentum={cvd_momentum:.4f} "
                f"(threshold={-self._veto_threshold}), price=${market.current_price:.2f} > "
                f"vwap=${self._vwap:.2f} | bearish divergence"
            )
            return Vote(
                agent_id=self.agent_id,
                direction=VoteDirection.HOLD,
                confidence=0.90,
                reasoning=reasoning,
            )

        # If cvd_momentum > +0.15 AND price < vwap * 0.99 → accumulation signal
        if cvd_momentum > self._veto_threshold and market.current_price < self._vwap * (1.0 - self._divergence_pct / 100):
            reasoning = (
                f"Accumulation detected: cvd_momentum={cvd_momentum:.4f} "
                f"(threshold={self._veto_threshold}), price=${market.current_price:.2f} < "
                f"vwap=${self._vwap:.2f} ({-self._divergence_pct:.1f}%)"
            )
            return Vote(
                agent_id=self.agent_id,
                direction=VoteDirection.BUY,
                confidence=min(0.75, abs(cvd_momentum) * 0.5 + 0.5),
                reasoning=reasoning,
            )

        # Step 5: Composite signal
        # Weights: CVD 50%, VWAP 30%, Imbalance 20%
        cvd_weight = max(-1.0, min(1.0, cvd_momentum))
        vwap_weight = 1.0 if vwap_deviation > self._divergence_pct else (
            -1.0 if vwap_deviation < -self._divergence_pct else 0.0
        )

        signal = (
            cvd_weight * 0.50 + vwap_weight * 0.30 + imbalance * 0.20
        )

        # Determine direction and confidence
        if signal > 0.08:
            direction = VoteDirection.BUY
            confidence = min(0.95, abs(signal))
        elif signal < -0.08:
            direction = VoteDirection.SELL
            confidence = min(0.95, abs(signal))
        else:
            direction = VoteDirection.HOLD
            confidence = max(0.05, 1.0 - abs(signal))

        # Ensure confidence bounds
        confidence = max(0.05, min(0.95, confidence))

        reasoning = (
            f"cvd_momentum={cvd_momentum:+.4f} | vwap_dev={vwap_deviation:+.2f}% | "
            f"imbalance={imbalance:+.2f} | signal={signal:+.4f}"
        )

        return Vote(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            reasoning=reasoning,
        )

    def boost(self, amount: float = 0.1):
        """Reward correct call — increase weight."""
        self.weight = min(5.0, self.weight + amount)
        self.consecutive_wrong = 0

    def punish(self, consecutive: bool = False):
        """Penalize wrong call — decrease weight."""
        self.weight = max(0.15, self.weight - 0.1)
        if consecutive:
            self.consecutive_wrong += 1
