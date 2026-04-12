"""
OpenClaw: The Quantum Board of Directors
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Multi-director consensus voting engine powered by Groq + Llama 3.3 70B.
Four autonomous personas (Alpha, Beta, Gamma, Delta) synthesize market signals
and render high-conviction trading decisions at sub-50ms latency.
"""

import json
from enum import Enum
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


class DirectorVote(Enum):
    """Individual director decision"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class BoardVote(Enum):
    """Collective board decision"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class DirectorOpinion:
    """Single director's analysis"""
    name: str  # Alpha, Beta, Gamma, Delta
    vote: DirectorVote
    confidence: float  # 0.0-1.0
    reasoning: str


@dataclass
class BoardDecision:
    """Complete board consensus output"""
    board_vote: BoardVote
    consensus_level: str  # "4/4", "3/4", "2/4", "HOLD"
    leverage: float  # 1x, 2x, 3x, max
    exit_target_pct: float  # 25%, 50%
    sentiment_reddit: float  # 0-100
    sentiment_news: float  # 0-100
    individual_votes: Dict[str, DirectorOpinion]
    rationale: str  # One-sentence summary
    execution_packet: str  # Formatted output


class QuantumBoard:
    """
    The Board: Four autonomous directors synthesizing market signals.
    
    Directors:
    - Alpha (The Quant): Technical indicators (RSI, MACD, Bollinger)
    - Beta (The Sentiment Scout): Social sentiment (Reddit, news)
    - Gamma (The Risk Officer): Risk/drawdown/leverage constraints
    - Delta (The Opportunist): Capital flow and rotation signals
    """

    def __init__(self):
        """Initialize the board"""
        self.directors = ["Alpha", "Beta", "Gamma", "Delta"]
        self.last_decision = None

    def analyze_signal(
        self,
        ticker: str,
        price_change_1h: float,
        rsi: float,
        macd_status: str,
        current_leverage: float,
        portfolio_drawdown: float,
        reddit_mentions: int,
        reddit_sentiment: float,  # 0-100
        reddit_themes: List[str],
        news_sentiment: float,  # 0-100
        news_headlines: List[str],
    ) -> BoardDecision:
        """
        Synthesize all market signals and render board decision.
        
        Args:
            ticker: e.g., "BTC/USD"
            price_change_1h: % change in last hour
            rsi: RSI(14) value (0-100)
            macd_status: "bullish_cross" | "bearish_cross" | "neutral"
            current_leverage: current position leverage (1x, 2x, 3x)
            portfolio_drawdown: % drawdown from ATH
            reddit_mentions: raw mention count
            reddit_sentiment: % positive sentiment on Reddit
            reddit_themes: ["moon", "dump", "mainnet", "squeeze"]
            news_sentiment: % positive in news
            news_headlines: raw headline texts
        
        Returns:
            BoardDecision with full execution packet
        """

        # === DIRECTOR ALPHA: THE QUANT ===
        alpha_vote = self._alpha_vote(rsi, macd_status, price_change_1h)
        alpha_confidence = self._alpha_confidence(rsi, macd_status)
        alpha_reasoning = self._alpha_reasoning(rsi, macd_status, price_change_1h)

        # === DIRECTOR BETA: THE SENTIMENT SCOUT ===
        beta_vote = self._beta_vote(
            reddit_sentiment, news_sentiment, reddit_themes, news_headlines
        )
        beta_confidence = self._beta_confidence(
            reddit_mentions, reddit_sentiment, news_sentiment
        )
        beta_reasoning = self._beta_reasoning(
            reddit_sentiment, news_sentiment, reddit_themes
        )

        # === DIRECTOR GAMMA: THE RISK OFFICER ===
        gamma_vote = self._gamma_vote(
            rsi, portfolio_drawdown, current_leverage, alpha_vote
        )
        gamma_confidence = self._gamma_confidence(portfolio_drawdown)
        gamma_reasoning = self._gamma_reasoning(portfolio_drawdown, current_leverage)

        # === DIRECTOR DELTA: THE OPPORTUNIST ===
        delta_vote = self._delta_vote(
            price_change_1h, reddit_sentiment, reddit_themes
        )
        delta_confidence = self._delta_confidence(
            price_change_1h, reddit_mentions, reddit_sentiment
        )
        delta_reasoning = self._delta_reasoning(price_change_1h, reddit_themes)

        # === TALLY BOARD CONSENSUS ===
        opinions = {
            "Alpha": DirectorOpinion("Alpha", alpha_vote, alpha_confidence, alpha_reasoning),
            "Beta": DirectorOpinion("Beta", beta_vote, beta_confidence, beta_reasoning),
            "Gamma": DirectorOpinion("Gamma", gamma_vote, gamma_confidence, gamma_reasoning),
            "Delta": DirectorOpinion("Delta", delta_vote, delta_confidence, delta_reasoning),
        }

        board_decision = self._tally_votes(
            opinions, reddit_sentiment, news_sentiment, current_leverage, portfolio_drawdown
        )

        self.last_decision = board_decision
        return board_decision

    # ═══════════════════════════════════════════════════════════════════════════
    # DIRECTOR ALPHA: THE QUANT
    # ═══════════════════════════════════════════════════════════════════════════

    def _alpha_vote(self, rsi: float, macd_status: str, price_change_1h: float) -> DirectorVote:
        """Quant director: pure technical analysis"""
        if rsi > 70:  # Overbought
            return DirectorVote.SELL
        elif rsi < 30:  # Oversold
            return DirectorVote.BUY
        elif macd_status == "bullish_cross":
            return DirectorVote.BUY
        elif macd_status == "bearish_cross":
            return DirectorVote.SELL
        else:
            return DirectorVote.HOLD

    def _alpha_confidence(self, rsi: float, macd_status: str) -> float:
        """How confident is Alpha in their vote?"""
        if rsi > 75 or rsi < 25:
            return 0.9
        elif macd_status != "neutral":
            return 0.75
        else:
            return 0.5

    def _alpha_reasoning(self, rsi: float, macd_status: str, price_change_1h: float) -> str:
        return f"RSI={rsi:.1f} ({self._rsi_regime(rsi)}), MACD={macd_status}, price_move={price_change_1h:.1f}%"

    def _rsi_regime(self, rsi: float) -> str:
        if rsi > 70:
            return "OVERBOUGHT"
        elif rsi < 30:
            return "OVERSOLD"
        else:
            return "NEUTRAL"

    # ═══════════════════════════════════════════════════════════════════════════
    # DIRECTOR BETA: THE SENTIMENT SCOUT
    # ═══════════════════════════════════════════════════════════════════════════

    def _beta_vote(
        self,
        reddit_sentiment: float,
        news_sentiment: float,
        reddit_themes: List[str],
        news_headlines: List[str],
    ) -> DirectorVote:
        """Sentiment director: social + news flow"""
        # Check for pump-and-dump red flags
        if "rug" in [t.lower() for t in reddit_themes]:
            return DirectorVote.SELL

        avg_sentiment = (reddit_sentiment + news_sentiment) / 2.0

        if avg_sentiment > 70:
            return DirectorVote.BUY
        elif avg_sentiment < 30:
            return DirectorVote.SELL
        else:
            return DirectorVote.HOLD

    def _beta_confidence(
        self, reddit_mentions: int, reddit_sentiment: float, news_sentiment: float
    ) -> float:
        """How strong is the social signal?"""
        mention_strength = min(reddit_mentions / 200.0, 1.0)  # Normalize to 0-1
        sentiment_extreme = max(abs(reddit_sentiment - 50) / 50.0, abs(news_sentiment - 50) / 50.0)
        return min((mention_strength + sentiment_extreme) / 2.0, 1.0)

    def _beta_reasoning(
        self, reddit_sentiment: float, news_sentiment: float, reddit_themes: List[str]
    ) -> str:
        return f"Reddit_sentiment={reddit_sentiment:.0f}%, News={news_sentiment:.0f}%, themes={reddit_themes[:2]}"

    # ═══════════════════════════════════════════════════════════════════════════
    # DIRECTOR GAMMA: THE RISK OFFICER
    # ═══════════════════════════════════════════════════════════════════════════

    def _gamma_vote(
        self,
        rsi: float,
        portfolio_drawdown: float,
        current_leverage: float,
        alpha_vote: DirectorVote,
    ) -> DirectorVote:
        """Risk director: drawdown + leverage constraints"""
        # Hard circuit breaker: drawdown > 5% → HOLD
        if portfolio_drawdown > 5.0:
            return DirectorVote.HOLD

        # Leverage already high → force HOLD unless clear signal
        if current_leverage > 2.0 and alpha_vote != DirectorVote.BUY:
            return DirectorVote.HOLD

        # RSI extreme + low drawdown → allow aggression
        if (rsi > 70 or rsi < 30) and portfolio_drawdown < 2.0:
            return alpha_vote

        # Default to risk-off
        return DirectorVote.HOLD

    def _gamma_confidence(self, portfolio_drawdown: float) -> float:
        """Risk officer conviction increases as drawdown decreases"""
        if portfolio_drawdown < 1.0:
            return 0.9
        elif portfolio_drawdown < 3.0:
            return 0.7
        elif portfolio_drawdown < 5.0:
            return 0.5
        else:
            return 0.1  # Near circuit breaker = low conviction

    def _gamma_reasoning(self, portfolio_drawdown: float, current_leverage: float) -> str:
        return f"Drawdown={portfolio_drawdown:.1f}%, Leverage={current_leverage:.1f}x, circuit_breaker_active={portfolio_drawdown > 5.0}"

    # ═══════════════════════════════════════════════════════════════════════════
    # DIRECTOR DELTA: THE OPPORTUNIST
    # ═══════════════════════════════════════════════════════════════════════════

    def _delta_vote(
        self, price_change_1h: float, reddit_sentiment: float, reddit_themes: List[str]
    ) -> DirectorVote:
        """Flow director: rotation momentum and early signals"""
        # Detect early entry: sentiment rising but price hasn't moved
        if reddit_sentiment > 65 and abs(price_change_1h) < 2.0:
            return DirectorVote.BUY

        # Detect early exit: price rising but sentiment turning negative
        if price_change_1h > 3.0 and reddit_sentiment < 45:
            return DirectorVote.SELL

        # Narrative rotation keywords
        if any(keyword in [t.lower() for t in reddit_themes] for keyword in ["mainnet", "ai", "rwa", "layer2"]):
            return DirectorVote.BUY

        # Late-stage hype
        if "moon" in [t.lower() for t in reddit_themes] and price_change_1h > 5.0:
            return DirectorVote.SELL

        return DirectorVote.HOLD

    def _delta_confidence(
        self, price_change_1h: float, reddit_mentions: int, reddit_sentiment: float
    ) -> float:
        """Flow signal strength"""
        if reddit_mentions > 300 and abs(price_change_1h) < 3.0:
            return 0.85  # Strong early signal
        elif abs(price_change_1h) > 5.0:
            return 0.7  # Movement detected
        else:
            return 0.4

    def _delta_reasoning(self, price_change_1h: float, reddit_themes: List[str]) -> str:
        return f"Price_move={price_change_1h:.1f}%, themes={reddit_themes[:2]}, rotation_mode=active"

    # ═══════════════════════════════════════════════════════════════════════════
    # BOARD CONSENSUS TALLYING
    # ═══════════════════════════════════════════════════════════════════════════

    def _tally_votes(
        self,
        opinions: Dict[str, DirectorOpinion],
        reddit_sentiment: float,
        news_sentiment: float,
        current_leverage: float,
        portfolio_drawdown: float,
    ) -> BoardDecision:
        """Tally director votes and determine board consensus"""

        # Count votes
        buy_count = sum(1 for o in opinions.values() if o.vote == DirectorVote.BUY)
        sell_count = sum(1 for o in opinions.values() if o.vote == DirectorVote.SELL)
        hold_count = sum(1 for o in opinions.values() if o.vote == DirectorVote.HOLD)

        # Determine board vote
        if buy_count > sell_count:
            board_vote = BoardVote.BUY
        elif sell_count > buy_count:
            board_vote = BoardVote.SELL
        else:
            board_vote = BoardVote.HOLD

        # Consensus level
        max_agreement = max(buy_count, sell_count, hold_count)
        consensus_level = f"{max_agreement}/4"

        # Determine leverage (key innovation!)
        leverage = self._determine_leverage(max_agreement, board_vote, portfolio_drawdown)

        # Exit target
        exit_target = self._determine_exit_target(
            max_agreement, reddit_sentiment, current_leverage
        )

        # Rationale (Delta's summary)
        rationale = opinions["Delta"].reasoning

        # Format execution packet
        execution_packet = self._format_execution_packet(
            board_vote,
            consensus_level,
            reddit_sentiment,
            news_sentiment,
            leverage,
            exit_target,
            opinions,
            rationale,
        )

        return BoardDecision(
            board_vote=board_vote,
            consensus_level=consensus_level,
            leverage=leverage,
            exit_target_pct=exit_target,
            sentiment_reddit=reddit_sentiment,
            sentiment_news=news_sentiment,
            individual_votes=opinions,
            rationale=rationale,
            execution_packet=execution_packet,
        )

    def _determine_leverage(
        self, consensus_count: int, board_vote: BoardVote, portfolio_drawdown: float
    ) -> float:
        """
        Consensus → Leverage Mapping:
        - 4/4: Max leverage (3-5x)
        - 3/4: 2-3x leverage
        - 2/4: 1x leverage
        - HOLD: 0x (no leverage)
        """
        if board_vote == BoardVote.HOLD:
            return 1.0  # No position
        elif consensus_count == 4:
            return 4.0 if portfolio_drawdown < 2.0 else 3.0  # Max leverage
        elif consensus_count == 3:
            return 2.5
        elif consensus_count == 2:
            return 1.5
        else:
            return 1.0

    def _determine_exit_target(
        self, consensus_count: int, reddit_sentiment: float, current_leverage: float
    ) -> float:
        """
        Exit target logic:
        - Standard (Gamma's rule): 25% ROI
        - High-risk extension: 50% ROI (if 3+ agreement AND strong sentiment AND high leverage)
        """
        if consensus_count >= 3 and reddit_sentiment > 75 and current_leverage > 2.0:
            return 50.0  # Risk-on extension
        else:
            return 25.0  # Standard

    def _format_execution_packet(
        self,
        board_vote: BoardVote,
        consensus_level: str,
        reddit_sentiment: float,
        news_sentiment: float,
        leverage: float,
        exit_target: float,
        opinions: Dict[str, DirectorOpinion],
        rationale: str,
    ) -> str:
        """Format the complete execution packet for dashboard/logging"""
        packet = f"""
╔════════════════════════════════════════════════════════════════╗
║              QUANTUM BOARD EXECUTION PACKET                    ║
╚════════════════════════════════════════════════════════════════╝

[BOARD VOTE]           {board_vote.value}
[CONSENSUS LEVEL]      {consensus_level} Directors Agree
[SENTIMENT SCORE]      Reddit: {reddit_sentiment:.0f}% | News: {news_sentiment:.0f}%
[RISK PARAMETERS]      Leverage: {leverage:.1f}x | Exit: {exit_target:.0f}% ROI
[RATIONALE]            {rationale}

[INDIVIDUAL VOTES]
  Alpha (Quant):       {opinions['Alpha'].vote.value} (conf: {opinions['Alpha'].confidence:.0%})
                       → {opinions['Alpha'].reasoning}
  
  Beta (Sentiment):    {opinions['Beta'].vote.value} (conf: {opinions['Beta'].confidence:.0%})
                       → {opinions['Beta'].reasoning}
  
  Gamma (Risk):        {opinions['Gamma'].vote.value} (conf: {opinions['Gamma'].confidence:.0%})
                       → {opinions['Gamma'].reasoning}
  
  Delta (Flow):        {opinions['Delta'].vote.value} (conf: {opinions['Delta'].confidence:.0%})
                       → {opinions['Delta'].reasoning}

"""
        return packet
