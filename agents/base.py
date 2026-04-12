"""
NEXUS Base Agent Framework — dataclasses and voting interface.
"""
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)


class VoteDirection(str, Enum):
    """Consensus vote direction."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Candle:
    """OHLCV candle from PRISM."""
    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PrismSignal:
    """AI-generated directional signal from PRISM /signals."""
    direction: str  # "neutral", "bullish", "bearish", "strong_bullish", "strong_bearish"
    confidence: float  # 0.0–1.0, computed from abs(net_score) / signal_count
    score: float  # -1.0 to +1.0, net_score normalised
    reasoning: str  # built from strength + active_signals
    indicators: dict = field(default_factory=dict)  # rsi, macd, macd_histogram, bollinger_upper, bollinger_lower
    current_price: float = 0.0  # from data[0]["current_price"]
    rsi: float = 0.0  # extracted from indicators for convenience
    macd_histogram: float = 0.0  # extracted from indicators for convenience
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class PrismRisk:
    """Risk metrics from PRISM /risk."""
    risk_score: float  # computed: min(100, max_drawdown * 2 + annual_volatility)
    atr_pct: float  # daily_volatility from response
    volatility_30d: float  # annual_volatility from response
    max_drawdown_30d: float  # max_drawdown from response
    sharpe_ratio: float  # sharpe_ratio from response
    sortino_ratio: float = 0.0  # sortino_ratio from response
    current_drawdown: float = 0.0  # current_drawdown from response
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class MarketData:
    """
    Canonical market data snapshot. Every agent reads from this single object.
    All fields populated by data/MarketDataBuilder.
    """
    # ALWAYS FIRST: required portfolio context (no defaults)
    pair: str
    current_price: float
    portfolio_value_usd: float
    open_position_usd: float
    
    # Candles and time (no defaults)
    candles: List[Candle] = field(default_factory=list)
    timestamp: int = field(default_factory=lambda: int(time.time()))
    
    # PRISM price endpoint (optional with defaults)
    change_24h_pct: float = 0.0
    volume_24h: float = 0.0
    cash_usd: float = 0.0

    # PRISM signals (two timeframes)
    signal_1h: Optional[PrismSignal] = None
    signal_4h: Optional[PrismSignal] = None

    # PRISM risk
    prism_risk: Optional[PrismRisk] = None

    # Sentiment inputs
    fear_greed_index: Optional[int] = None  # 0–100
    news_sentiment: Optional[float] = None  # -1.0 to +1.0
    social_score: Optional[float] = None  # 0.0–1.0, from CoinGecko community data

    # Order Flow microstructure (Task A)
    cvd: Optional[float] = None  # Cumulative Volume Delta
    vwap: Optional[float] = None  # Volume-Weighted Average Price
    bid_ask_imbalance: Optional[float] = None  # -1.0 (all sells) to +1.0 (all buys)

    def closes(self) -> List[float]:
        """Extract close prices."""
        return [c.close for c in self.candles]

    def highs(self) -> List[float]:
        """Extract high prices."""
        return [c.high for c in self.candles]

    def lows(self) -> List[float]:
        """Extract low prices."""
        return [c.low for c in self.candles]

    def volumes(self) -> List[float]:
        """Extract volumes."""
        return [c.volume for c in self.candles]


@dataclass
class Vote:
    """Agent vote in consensus cycle."""
    agent_id: str
    direction: VoteDirection
    confidence: float  # 0.0–1.0
    reasoning: str
    component_scores: dict = field(default_factory=dict)  # For logging
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class TradeDecision:
    """Consensus output for a trade cycle."""
    direction: VoteDirection
    confidence: float
    position_size_usd: float
    reasoning: str
    agent_votes: List[Vote]
    veto_reason: Optional[str] = None  # If vetoed, explain why
    timestamp: int = field(default_factory=lambda: int(time.time()))


class BaseAgent:
    """Base class for all trading agents."""

    def __init__(self, agent_id: str, reasoning: str = "Generic trading agent.", **kwargs):
        self.agent_id = agent_id
        self.reasoning = reasoning
        self.weight = kwargs.get('weight', 1.0)  # Default voting weight
        self.consecutive_wrong = 0  # Track consecutive wrong predictions
        # Catch any extra kwargs to prevent TypeError in subclasses
        if kwargs:
            logger.debug(f"BaseAgent {agent_id}: unused kwargs ignored: {list(kwargs.keys())}")

    def analyze(self, market_data: MarketData) -> Vote:
        """
        Analyze market data and return a vote.
        Must be implemented by subclasses.
        """
        raise NotImplementedError(f"{self.agent_id} must implement analyze()")
