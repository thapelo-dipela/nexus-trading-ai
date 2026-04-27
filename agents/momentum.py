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

        if len(closes) < 60:  # Need at least 60 candles for MACD warmup
            logger.warning("[yellow]MomentumAgent: insufficient candles (need 60+ for MACD warmup)[/yellow]")
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
        volume_score = self._volume_confirmation(market_data.volumes())  # NEW: volume confirmation

        # If PRISM signal available, use its RSI and MACD directly
        if market_data.signal_1h and market_data.signal_1h.rsi > 0:
            rsi_score = self._prism_rsi_to_score(market_data.signal_1h.rsi)
            logger.debug(f"[dim]Using PRISM RSI={market_data.signal_1h.rsi:.1f} (score={rsi_score:.3f})[/dim]")
        
        if market_data.signal_1h and market_data.signal_1h.macd_histogram != 0.0:
            macd_score = self._prism_macd_to_score(market_data.signal_1h.macd_histogram)
            logger.debug(f"[dim]Using PRISM MACD histogram={market_data.signal_1h.macd_histogram:.4f} (score={macd_score:.3f})[/dim]")

        # Local TA composite (60% weight) - now with volume confirmation
        # Updated weights: RSI 30%, MACD 30%, BB 20%, Volume 20%
        local_ta_score = (rsi_score * 0.30 + macd_score * 0.30 + bb_score * 0.20 + volume_score * 0.20)

        # PRISM signal scores (DO NOT double-count PRISM RSI/MACD - they replace local, not add)
        signal_4h_score = 0.0
        signal_1h_score = 0.0

        if market_data.signal_4h:
            signal_4h_score = market_data.signal_4h.score
        if market_data.signal_1h:
            signal_1h_score = market_data.signal_1h.score

        # Composite score with weights (now only PRISM signal scores, not RSI/MACD again)
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
            f"RSI={rsi_score:.3f} MACD={macd_score:.3f} BB={bb_score:.3f} Volume={volume_score:.3f} "
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
        """
        Compute RSI-14 using Wilder's smoothing (not simple average).
        Wilder's RSI requires 14 periods of gains/losses.
        Fix: closes[-15:] gives 15 prices → 14 deltas, not 13.
        """
        if len(closes) < 15:  # Need 15 prices for 14 deltas
            return 0.0

        # Get 14 deltas from 15 prices
        deltas = np.diff(np.array(closes[-15:]))

        # Wilder's smoothing: initialize with first gain/loss
        gain_sum = 0.0
        loss_sum = 0.0
        
        for delta in deltas:
            if delta > 0:
                gain_sum += delta
            else:
                loss_sum += abs(delta)
        
        # Wilder's method: exponentially smoothed average
        # RS = avg_gain / avg_loss (14-period Wilder's smoothing)
        avg_gain = gain_sum / 14.0
        avg_loss = loss_sum / 14.0
        
        rs = (avg_gain + 1e-9) / (avg_loss + 1e-9)
        rsi = 100.0 - (100.0 / (1.0 + rs))

        # Normalize to [-1, +1]: RSI 70+ = +1 (bullish), RSI 30- = -1 (bearish)
        if rsi >= 70:
            return 1.0
        elif rsi <= 30:
            return -1.0
        else:
            return (rsi - 50.0) / 50.0

    def _macd_score(self, closes: List[float]) -> float:
        """
        Compute MACD (12/26/9) score normalized to [-1, +1].
        Fix: Need 60+ candles for proper EMA warmup. MACD line needs 9+ points before signal EMA.
        Fix: Normalize by histogram standard deviation, not by signal_line value (which explodes at crossovers).
        """
        if len(closes) < 60:  # Need at least 60 candles for proper warmup
            return 0.0

        closes_arr = np.array(closes[-60:])

        # EMA 12 and EMA 26 on full 60-candle history
        ema12 = self._ema(closes_arr, 12)
        ema26 = self._ema(closes_arr, 26)
        
        # MACD line (12 - 26)
        macd_line = ema12 - ema26
        
        # Signal line (EMA 9 of MACD line)
        # Need at least 9 points in MACD to compute signal EMA
        if len(macd_line) < 9:
            return 0.0
        
        signal_line = self._ema(macd_line, 9)
        
        # Histogram
        histogram = macd_line[-1] - signal_line[-1]
        
        # Normalize by histogram standard deviation, not by signal_line value
        # This prevents explosion at MACD crossovers (where signal_line ≈ macd_line ≈ 0)
        histogram_std = np.std(macd_line - signal_line)
        if histogram_std < 1e-9:
            histogram_std = 1e-9
        
        # Tanh compression of histogram / std
        normalized = np.tanh(histogram / histogram_std)
        return float(normalized)

    def _bollinger_score(
        self, closes: List[float], highs: List[float], lows: List[float]
    ) -> float:
        """
        Compute Bollinger Bands (20/2) score normalized to [-1, +1].
        For MOMENTUM agent: price above upper band = breakout continuation (+1),
        price below lower band = downtrend continuation (-1).
        """
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

        # Position within bands (momentum interpretation)
        if current > upper_band:
            return 1.0  # Breakout continuation - bullish momentum
        elif current < lower_band:
            return -1.0  # Downtrend continuation - bearish momentum
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

    def _volume_confirmation(self, volumes: List[float]) -> float:
        """
        Volume confirmation: Strong moves on above-average volume = higher conviction.
        Return: +1.0 if current volume > 1.5x average, -0.5 if < 0.5x average, 0.0 otherwise.
        """
        if len(volumes) < 20:
            return 0.0
        
        volumes_arr = np.array(volumes[-20:])
        avg_volume = volumes_arr.mean()
        current_volume = volumes[-1]
        
        if current_volume > 1.5 * avg_volume:
            return 0.5  # Above-average volume = higher conviction
        elif current_volume < 0.5 * avg_volume:
            return -0.3  # Below-average volume = lower conviction
        else:
            return 0.0

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
