"""
NEXUS Mean Reversion Agent — detects oversold/overbought conditions.
Negatively correlated with momentum; provides signal diversity.
"""
import logging
from typing import Optional

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

            # Price distance from moving average
            sma_score = self._price_distance_from_sma_score(market_data)

            # Composite: equally weighted
            composite = (rsi_score + bb_score + sma_score) / 3.0

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
        RSI oversold/overbought detection.
        Returns: [-1, +1] where -1 = overbought (SELL), +1 = oversold (BUY)
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
        """
        if len(market_data.candles) < 20:
            return 0.0

        closes = [c.close for c in market_data.candles[-20:]]
        sma = sum(closes) / 20
        variance = sum((x - sma) ** 2 for x in closes) / 20
        std_dev = variance ** 0.5

        upper_band = sma + 2 * std_dev
        lower_band = sma - 2 * std_dev

        current_price = market_data.current_price

        # Beyond upper band = overbought = SELL
        if current_price > upper_band:
            excess = (current_price - upper_band) / std_dev
            return max(-1.0, -0.5 * (excess / 3.0))  # capped at -1

        # Below lower band = oversold = BUY
        elif current_price < lower_band:
            excess = (lower_band - current_price) / std_dev
            return min(1.0, 0.5 * (excess / 3.0))  # capped at +1

        return 0.0

    def _price_distance_from_sma_score(self, market_data: MarketData) -> float:
        """
        Mean reversion signal: distance from 50-period SMA.
        Returns: [-1, +1]
        """
        if len(market_data.candles) < 50:
            return 0.0

        closes = [c.close for c in market_data.candles[-50:]]
        sma_50 = sum(closes) / 50
        current_price = market_data.current_price

        distance_pct = (current_price - sma_50) / sma_50

        # More than 3% above SMA = overbought = SELL
        if distance_pct > 0.03:
            return max(-1.0, -min(1.0, distance_pct))

        # More than 3% below SMA = oversold = BUY
        elif distance_pct < -0.03:
            return min(1.0, -distance_pct)

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
