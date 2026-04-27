"""
NEXUS Mean Reversion Agent — detects oversold/overbought conditions.
Negatively correlated with momentum; provides signal diversity.
"""
import logging
from typing import Optional
import numpy as np

from agents.base import Vote, VoteDirection, MarketData, BaseAgent

logger = logging.getLogger(__name__)


class MeanReversionAgent(BaseAgent):
    """
    Mean reversion strategy:
    - Oversold (RSI < 30) → BUY signal
    - Overbought (RSI > 70) → SELL signal
    - Combines with Bollinger Band mean reversion
    - Contrarian to momentum agent
    """

    def __init__(self, agent_id: str = "mean_reversion", reasoning: str = "Mean reversion strategy based on RSI, Bollinger Bands, and SMA."):
        super().__init__(agent_id, reasoning)

    def analyze(self, market_data: MarketData) -> Optional[Vote]:
        """
        Compute mean reversion score.
        Returns: Vote with direction and confidence
        """
        try:
            if not market_data.candles or len(market_data.candles) < 14:
                return None

            # RSI for oversold/overbought
            rsi_score = self._rsi_oversold_overbought_score(market_data)

            # Bollinger Band mean reversion
            bb_score = self._bollinger_mean_reversion_score(market_data)

            # Price distance from moving average (with trend filter)
            sma_score = self._price_distance_from_sma_score(market_data)

            # Add trend filter to suppress mean reversion in strong trends
            trend_filter = self._get_trend_filter(market_data)

            # Composite: weighted (RSI 40%, BB 35%, SMA 25%)
            composite = (rsi_score * 0.40 + bb_score * 0.35 + sma_score * 0.25)
            
            # Apply trend filter: reduces signal confidence if in strong trend
            if trend_filter != 0.0:
                composite *= abs(trend_filter)  # Reduce by trend strength

            # Determine direction and confidence
            if composite > 0.3:
                direction = VoteDirection.BUY
                confidence = min(0.95, 0.3 + abs(composite))
            elif composite < -0.3:
                direction = VoteDirection.SELL
                confidence = min(0.95, 0.3 + abs(composite))
            else:
                direction = VoteDirection.HOLD
                confidence = 0.1

            logger.debug(
                f"[dim]mean_reversion: {direction.value} (conf={confidence:.3f}) "
                f"rsi={rsi_score:.3f}, bb={bb_score:.3f}, sma={sma_score:.3f}[/dim]"
            )

            return Vote(
                agent_id=self.agent_id,
                direction=direction,
                confidence=confidence,
                reasoning=f"MeanReversion: rsi={rsi_score:.3f} bb={bb_score:.3f} sma={sma_score:.3f} composite={composite:.3f}",
                component_scores={"rsi": rsi_score, "bb": bb_score, "sma": sma_score, "composite": composite},
            )

        except Exception as e:
            logger.error(f"[red]MeanReversionAgent exception: {e}[/red]")
            return None

    def _rsi_oversold_overbought_score(self, market_data: MarketData) -> float:
        """
        RSI oversold/overbought detection using Wilder's smoothing.
        Returns: [-1, +1] where -1 = overbought (SELL), +1 = oversold (BUY)
        Fix: Use 15 prices for 14 deltas, implement Wilder's smoothing.
        """
        rsi = self._compute_rsi(market_data.candles, period=14)
        if rsi is None:
            return 0.0

        # Map RSI to score
        # RSI < 30 = oversold = BUY = +1
        # RSI > 70 = overbought = SELL = -1
        # RSI 30-70 = neutral = 0
        if rsi < 30:
            return min(1.0, (30 - rsi) / 30)  # stronger at lower RSI
        elif rsi > 70:
            return max(-1.0, -(rsi - 70) / 30)  # stronger at higher RSI
        else:
            return 0.0

    def _bollinger_mean_reversion_score(self, market_data: MarketData) -> float:
        """
        Bollinger Band mean reversion: price beyond bands suggests reversion.
        Returns: [-1, +1]
        Fix: Properly calibrate to reach ±1.0 at maximum extension, not capped at ±0.5.
        """
        if len(market_data.candles) < 20:
            return 0.0

        closes = [c.close for c in market_data.candles[-20:]]
        sma = sum(closes) / 20
        variance = sum((x - sma) ** 2 for x in closes) / 20
        std_dev = variance ** 0.5

        if std_dev == 0:
            return 0.0

        upper_band = sma + 2 * std_dev
        lower_band = sma - 2 * std_dev

        current_price = market_data.current_price

        # Beyond upper band = overbought = SELL (signal magnitude based on extension)
        if current_price > upper_band:
            excess = (current_price - upper_band) / std_dev
            # Properly scale to reach -1.0 at strong extension (excess = 2.0)
            return max(-1.0, min(-0.0, -excess / 2.0))

        # Below lower band = oversold = BUY (signal magnitude based on extension)
        elif current_price < lower_band:
            excess = (lower_band - current_price) / std_dev
            # Properly scale to reach +1.0 at strong extension (excess = 2.0)
            return min(1.0, max(0.0, excess / 2.0))

        return 0.0

    def _price_distance_from_sma_score(self, market_data: MarketData) -> float:
        """
        Mean reversion signal: distance from 50-period SMA.
        Returns: [-1, +1]
        Fix: Threshold increased from 3% to 5-8% for crypto (prevents false signals in trends).
        """
        if len(market_data.candles) < 50:
            return 0.0

        closes = [c.close for c in market_data.candles[-50:]]
        sma_50 = sum(closes) / 50
        current_price = market_data.current_price

        distance_pct = (current_price - sma_50) / sma_50

        # More than 7% above SMA = overbought = SELL
        if distance_pct > 0.07:
            return max(-1.0, min(-0.0, -(distance_pct / 0.15)))  # scale to ±1

        # More than 7% below SMA = oversold = BUY
        elif distance_pct < -0.07:
            return min(1.0, max(0.0, -distance_pct / 0.15))  # scale to ±1

        return 0.0

    def _get_trend_filter(self, market_data: MarketData) -> float:
        """
        Trend filter: Suppress mean reversion signals during strong trends.
        Returns: 0.0 if trend is strong, 1.0 if no strong trend.
        Uses 200-SMA: if price > 200-SMA = uptrend (suppress SELL), if price < 200-SMA = downtrend (suppress BUY).
        """
        if len(market_data.candles) < 200:
            return 1.0  # No filter if insufficient history
        
        closes = [c.close for c in market_data.candles[-200:]]
        sma_200 = sum(closes) / 200
        current_price = market_data.current_price
        
        # If in strong uptrend (price > 200-SMA by >2%), suppress mean reversion SELL signals
        if current_price > sma_200 * 1.02:
            return 0.5  # Reduce mean reversion signal strength
        
        # If in strong downtrend (price < 200-SMA by >2%), suppress mean reversion BUY signals
        elif current_price < sma_200 * 0.98:
            return 0.5  # Reduce mean reversion signal strength
        
        return 1.0  # No trend, full signal strength

    def _rsi_divergence_score(self, market_data: MarketData) -> float:
        """
        RSI divergence detection: A powerful mean reversion signal.
        Price making higher highs while RSI makes lower highs = bearish divergence = SELL signal.
        Price making lower lows while RSI makes higher lows = bullish divergence = BUY signal.
        Returns: [-1, +1]
        """
        if len(market_data.candles) < 30:
            return 0.0
        
        candles = market_data.candles[-30:]
        closes = [c.close for c in candles]
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        
        rsi_values = [self._compute_rsi_single([c.close for c in market_data.candles[max(0, i-13):i+1]], 14) 
                     for i in range(13, len(candles))]
        
        if len(rsi_values) < 3:
            return 0.0
        
        # Check for bearish divergence (higher price high, lower RSI high)
        recent_price_high = max(highs[-3:])
        recent_rsi_high = max(rsi_values[-3:])
        prev_price_high = max(highs[-6:-3])
        prev_rsi_high = max(rsi_values[-6:-3])
        
        if recent_price_high > prev_price_high and recent_rsi_high < prev_rsi_high:
            return -0.6  # Bearish divergence = SELL (but not as strong as direct oversold)
        
        # Check for bullish divergence (lower price low, higher RSI low)
        recent_price_low = min(lows[-3:])
        recent_rsi_low = min(rsi_values[-3:])
        prev_price_low = min(lows[-6:-3])
        prev_rsi_low = min(rsi_values[-6:-3])
        
        if recent_price_low < prev_price_low and recent_rsi_low > prev_rsi_low:
            return 0.6  # Bullish divergence = BUY (but not as strong as direct oversold)
        
        return 0.0

    def _compute_rsi(self, candles, period: int = 14) -> Optional[float]:
        """Compute RSI (14-period default)."""
        if len(candles) < period + 1:
            return None

        deltas = [candles[i].close - candles[i - 1].close for i in range(1, len(candles))]
        gains = [max(0, d) for d in deltas[-period:]]
        losses = [max(0, -d) for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _compute_rsi_single(self, closes: list, period: int = 14) -> Optional[float]:
        """Compute RSI from a list of prices (closes)."""
        if len(closes) < period + 1:
            return None

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        gains = [max(0, d) for d in deltas[-period:]]
        losses = [max(0, -d) for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
