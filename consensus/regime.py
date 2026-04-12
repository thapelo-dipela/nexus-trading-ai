"""
NEXUS Regime Detector — classify market regime and dynamically re-weight agents.
Regimes: trending, ranging, high-volatility.
"""
import logging
from enum import Enum
from typing import Optional

from agents.base import MarketData

logger = logging.getLogger(__name__)


class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING = "trending"
    RANGING = "ranging"
    HIGH_VOLATILITY = "high_volatility"


class RegimeDetector:
    """
    Detect market regime using ADX (Average Directional Index).
    - ADX > 25: Strong trend
    - ADX 20-25: Moderate trend
    - ADX < 20: Range-bound or choppy
    Also considers ATR for volatility regime.
    """

    def __init__(self):
        pass

    def detect_regime(self, market_data: MarketData) -> MarketRegime:
        """
        Classify current market regime.
        Returns: MarketRegime (TRENDING, RANGING, or HIGH_VOLATILITY)
        """
        if not market_data.candles or len(market_data.candles) < 14:
            return MarketRegime.RANGING  # Default to ranging if insufficient data

        adx = self._compute_adx(market_data.candles, period=14)
        atr_pct = self._compute_atr_pct(market_data.candles, market_data.current_price, period=14)

        # High volatility regime (ATR > 2% of price)
        if atr_pct > 0.02:
            return MarketRegime.HIGH_VOLATILITY

        # Trending regime (ADX strong)
        if adx > 25:
            return MarketRegime.TRENDING

        # Ranging regime
        return MarketRegime.RANGING

    def get_agent_weights(self, regime: MarketRegime) -> dict:
        """
        Return dynamic weight adjustments for each agent based on regime.
        Format: {"agent_id": weight_multiplier}
        
        Multipliers > 1.0 boost the agent; < 1.0 reduce it.
        """
        weights = {
            "momentum": 1.0,
            "sentiment": 1.0,
            "risk_guardian": 1.0,
            "mean_reversion": 1.0,
        }

        if regime == MarketRegime.TRENDING:
            # Momentum performs well in trends
            weights["momentum"] = 1.5
            weights["mean_reversion"] = 0.5  # Struggles in trends
            weights["sentiment"] = 0.8
            weights["risk_guardian"] = 1.0

        elif regime == MarketRegime.RANGING:
            # Mean reversion performs well in ranges
            weights["mean_reversion"] = 1.5
            weights["sentiment"] = 1.2  # Sentiment can spot range boundaries
            weights["momentum"] = 0.6  # Momentum whipsawed in ranges
            weights["risk_guardian"] = 1.0

        elif regime == MarketRegime.HIGH_VOLATILITY:
            # Risk guardian dominates; others take a backseat
            weights["risk_guardian"] = 2.0
            weights["momentum"] = 0.7
            weights["mean_reversion"] = 0.5
            weights["sentiment"] = 0.6

        return weights

    def _compute_adx(self, candles, period: int = 14) -> Optional[float]:
        """
        Compute Average Directional Index (ADX).
        Returns: ADX value (0-100), higher = stronger trend.
        """
        if len(candles) < period + 1:
            return None

        # Compute +DM, -DM, True Range
        plus_dm_list = []
        minus_dm_list = []
        tr_list = []

        for i in range(1, len(candles)):
            high_diff = candles[i].high - candles[i - 1].high
            low_diff = candles[i - 1].low - candles[i].low

            # +DM
            plus_dm = 0
            if high_diff > 0 and high_diff > low_diff:
                plus_dm = high_diff

            # -DM
            minus_dm = 0
            if low_diff > 0 and low_diff > high_diff:
                minus_dm = low_diff

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

            # True Range
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i - 1].close),
                abs(candles[i].low - candles[i - 1].close),
            )
            tr_list.append(tr)

        # Smooth +DM, -DM, TR using exponential moving average
        def ema(values, period):
            if not values or len(values) < period:
                return None
            ema_val = sum(values[:period]) / period
            multiplier = 2 / (period + 1)
            for val in values[period:]:
                ema_val = val * multiplier + ema_val * (1 - multiplier)
            return ema_val

        smoothed_plus_dm = ema(plus_dm_list, period)
        smoothed_minus_dm = ema(minus_dm_list, period)
        smoothed_tr = ema(tr_list, period)

        if not smoothed_tr or smoothed_tr == 0:
            return 0.0

        # Directional indicators
        di_plus = 100 * (smoothed_plus_dm / smoothed_tr)
        di_minus = 100 * (smoothed_minus_dm / smoothed_tr)

        # ADX
        dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0
        adx = dx  # Simplified; proper ADX uses EMA of DX

        return adx

    def _compute_atr_pct(self, candles, current_price: float, period: int = 14) -> float:
        """Compute ATR as percentage of current price."""
        if len(candles) < period or current_price == 0:
            return 0.0

        tr_list = []
        for i in range(1, min(len(candles), period + 1)):
            tr = max(
                candles[i].high - candles[i].low,
                abs(candles[i].high - candles[i - 1].close),
                abs(candles[i].low - candles[i - 1].close),
            )
            tr_list.append(tr)

        atr = sum(tr_list) / len(tr_list)
        return atr / current_price
