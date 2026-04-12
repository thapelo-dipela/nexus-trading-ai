"""
MomentumAgent — blends local technical analysis with PRISM multi-timeframe signals.
"""
import logging
from typing import List
import numpy as np

from agents.base import BaseAgent, MarketData, Vote, VoteDirection

logger = logging.getLogger(__name__)


class MomentumAgent(BaseAgent):
    """
    Blends local technical analysis with PRISM signals:
    - Local TA (RSI-14, MACD 12/26/9, Bollinger Bands 20/2): 60% composite weight
    - PRISM 4h signal score: 25% weight
    - PRISM 1h signal score: 15% weight
    """

    def __init__(self, agent_id: str = "momentum", reasoning: str = "Blends local technical analysis with PRISM multi-timeframe signals."):
        super().__init__(agent_id, reasoning)

    def analyze(self, market_data: MarketData) -> Vote:
        """Analyze market data and return a vote."""
        closes = market_data.closes()

        if len(closes) < 26:  # Need at least 26 candles for MACD
            logger.warning("[yellow]MomentumAgent: insufficient candles[/yellow]")
            return Vote(
                agent_id=self.agent_id,
                direction=VoteDirection.HOLD,
                confidence=0.1,
                reasoning="Insufficient candles for momentum analysis",
            )

        # Compute local TA scores
        rsi_score = self._rsi_score(closes)
        macd_score = self._macd_score(closes)
        bb_score = self._bollinger_score(closes, market_data.highs(), market_data.lows())

        # If PRISM signal available, use its RSI and MACD directly
        if market_data.signal_1h and market_data.signal_1h.rsi > 0:
            rsi_score = self._prism_rsi_to_score(market_data.signal_1h.rsi)
            logger.debug(f"[dim]Using PRISM RSI={market_data.signal_1h.rsi:.1f} (score={rsi_score:.3f})[/dim]")
        
        if market_data.signal_1h and market_data.signal_1h.macd_histogram != 0.0:
            macd_score = self._prism_macd_to_score(market_data.signal_1h.macd_histogram)
            logger.debug(f"[dim]Using PRISM MACD histogram={market_data.signal_1h.macd_histogram:.4f} (score={macd_score:.3f})[/dim]")

        # Local TA composite (60% weight)
        local_ta_score = (rsi_score + macd_score + bb_score) / 3.0

        # PRISM signal scores
        signal_4h_score = 0.0
        signal_1h_score = 0.0

        if market_data.signal_4h:
            signal_4h_score = market_data.signal_4h.score
        if market_data.signal_1h:
            signal_1h_score = market_data.signal_1h.score

        # Composite score with weights
        composite = (local_ta_score * 0.60) + (signal_4h_score * 0.25) + (signal_1h_score * 0.15)

        # Log with PRISM details at dim level
        if market_data.signal_1h:
            logger.debug(
                f"[dim]PRISM: dir={market_data.signal_1h.direction} rsi={market_data.signal_1h.rsi:.1f} "
                f"macd_hist={market_data.signal_1h.macd_histogram:.4f} price=${market_data.signal_1h.current_price:,.2f}[/dim]"
            )

        # Log component scores at dim level
        logger.debug(
            f"[dim]MomentumAgent components: "
            f"RSI={rsi_score:.3f} MACD={macd_score:.3f} BB={bb_score:.3f} "
            f"Local={local_ta_score:.3f} Signal4h={signal_4h_score:.3f} Signal1h={signal_1h_score:.3f} "
            f"Composite={composite:.3f}[/dim]"
        )

        # Determine direction and confidence
        threshold = 0.15
        if composite > threshold:
            direction = VoteDirection.BUY
            confidence = float(np.clip(abs(composite), 0.0, 1.0))
        elif composite < -threshold:
            direction = VoteDirection.SELL
            confidence = float(np.clip(abs(composite), 0.0, 1.0))
        else:
            direction = VoteDirection.HOLD
            confidence = 0.1

        return Vote(
            agent_id=self.agent_id,
            direction=direction,
            confidence=confidence,
            reasoning=f"Momentum composite: {composite:.3f}",
            component_scores={
                "local_ta": local_ta_score,
                "signal_4h": signal_4h_score,
                "signal_1h": signal_1h_score,
                "composite": composite,
            },
        )

    def _rsi_score(self, closes: List[float]) -> float:
        """Compute RSI-14 score normalized to [-1, +1]."""
        if len(closes) < 14:
            return 0.0

        deltas = np.diff(closes[-14:])
        seed = deltas[:1]
        up = seed[0] if seed[0] > 0 else 0.0
        down = -seed[0] if seed[0] < 0 else 0.0

        ups = np.zeros_like(deltas)
        downs = np.zeros_like(deltas)
        ups[deltas > 0] = deltas[deltas > 0]
        downs[deltas < 0] = -deltas[deltas < 0]

        rs = (ups.sum() / 14.0 + 1e-9) / (downs.sum() / 14.0 + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # Normalize to [-1, +1]: RSI 70+ = +1 (bullish), RSI 30- = -1 (bearish)
        if rsi >= 70:
            return 1.0
        elif rsi <= 30:
            return -1.0
        else:
            return (rsi - 50.0) / 50.0

    def _macd_score(self, closes: List[float]) -> float:
        """Compute MACD (12/26/9) score normalized to [-1, +1]."""
        if len(closes) < 26:
            return 0.0

        closes_arr = np.array(closes[-26:])

        # EMA 12
        ema12 = self._ema(closes_arr, 12)
        # EMA 26
        ema26 = self._ema(closes_arr, 26)
        # MACD line
        macd_line = ema12 - ema26

        # Signal line (EMA 9 of MACD)
        if len(macd_line) < 9:
            return 0.0
        signal_line = self._ema(macd_line, 9)

        # Histogram
        histogram = macd_line[-1] - signal_line[-1]

        # Normalize to [-1, +1]
        normalized = np.tanh(histogram / max(abs(signal_line[-1]), 1e-9))
        return float(normalized)

    def _bollinger_score(
        self, closes: List[float], highs: List[float], lows: List[float]
    ) -> float:
        """Compute Bollinger Bands (20/2) score normalized to [-1, +1]."""
        if len(closes) < 20:
            return 0.0

        closes_arr = np.array(closes[-20:])
        sma = closes_arr.mean()
        std = closes_arr.std()

        if std == 0:
            return 0.0

        upper_band = sma + (2 * std)
        lower_band = sma - (2 * std)
        current = closes[-1]

        # Position within bands
        if current > upper_band:
            return 1.0  # Overbought
        elif current < lower_band:
            return -1.0  # Oversold
        else:
            # Linear interpolation within bands
            band_width = upper_band - lower_band
            normalized = (current - sma) / (band_width / 2.0)
            return max(-1.0, min(1.0, normalized))

    @staticmethod
    def _ema(values: np.ndarray, period: int) -> np.ndarray:
        """Compute exponential moving average."""
        if len(values) == 0:
            return np.array([])
        multiplier = 2.0 / (period + 1)
        ema = np.zeros_like(values, dtype=float)
        ema[0] = values[0]
        for i in range(1, len(values)):
            ema[i] = values[i] * multiplier + ema[i - 1] * (1 - multiplier)
        return ema

    @staticmethod
    def _prism_rsi_to_score(rsi: float) -> float:
        """Convert PRISM RSI (0-100) to normalized score [-1, +1]."""
        if rsi >= 70:
            return 1.0
        elif rsi <= 30:
            return -1.0
        else:
            return (rsi - 50.0) / 50.0

    @staticmethod
    def _prism_macd_to_score(macd_histogram: float) -> float:
        """Convert PRISM MACD histogram to normalized score [-1, +1]."""
        normalized = np.tanh(macd_histogram / max(abs(macd_histogram), 1e-9))
        return float(normalized)
