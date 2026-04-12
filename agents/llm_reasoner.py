"""
LLMReasonerAgent — Meta-reasoning via Groq + Llama 3.3 70B + OpenClaw
Source: komalvsingh/TradeAgent + OpenClaw Quantum Board
Contributes: EIP-712 auditable rationale for every trade decision via LLM

This agent runs AFTER other agents vote. It receives their votes, market data,
and position state, then calls Groq Llama 3.3 70B through the OpenClaw Board
to produce a multi-director consensus vote that adjudicates conflicts and
provides an auditable rationale checkpoint.
"""

import logging
import json
import time
from typing import List, Optional, Dict, Any
import config
from agents.base import BaseAgent, Vote, VoteDirection, MarketData
from openclaw import QuantumBoard

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False


class LLMReasonerAgent(BaseAgent):
    """
    Special agent that runs AFTER other agents vote.
    Receives their votes as context and reasons about conflicts using
    the OpenClaw Quantum Board (4 autonomous directors).
    Weight starts at 2.0 (6th position, high voting power).
    
    Directors:
    - Alpha: Technical analysis (RSI, MACD)
    - Beta: Social sentiment (Reddit, news)
    - Gamma: Risk management & capital preservation
    - Delta: Capital rotation & flow signals
    """

    def __init__(self, groq_api_key: str = ""):
        super().__init__("llm_reasoner", reasoning="Quantum Board + Groq Llama 3.3 70B")
        self.weight = 2.0  # 6th position in voting hierarchy
        self._api_key = groq_api_key or config.GROQ_API_KEY
        self._client = None
        self._board = QuantumBoard()  # Initialize the 4-director consensus engine
        self._last_decision: Optional[Dict[str, Any]] = None
        self._timeout = config.LLM_REASONER_TIMEOUT
        self.consecutive_wrong = 0

        if self._api_key and HAS_GROQ:
            try:
                self._client = Groq(api_key=self._api_key)
                logger.info("[dim]LLMReasonerAgent initialized with Groq API + OpenClaw[/dim]")
            except Exception as e:
                logger.warning(f"[dim]Failed to initialize Groq client: {e}[/dim]")
                self._client = None
        else:
            logger.info("[dim]Groq API not configured; using local OpenClaw board only[/dim]")

    def analyze(self, market: MarketData) -> Vote:
        """
        Called without prior votes — returns HOLD.
        Use vote_with_context() instead for the real analysis.
        """
        return Vote(
            agent_id=self.agent_id,
            direction=VoteDirection.HOLD,
            confidence=0.1,
            reasoning="No context provided — call vote_with_context() instead",
        )

    def vote_with_context(
        self,
        market: MarketData,
        prior_votes: List[Vote],
        position_state: Dict[str, Any],
    ) -> Vote:
        """
        Main entry point for LLM reasoning via OpenClaw Board.
        Runs the 4-director consensus engine and optionally calls Groq for
        additional LLM-powered sentiment analysis.

        Args:
            market: Current market data snapshot
            prior_votes: List of Vote objects from other agents
            position_state: Current portfolio state (open positions, cash, etc.)

        Returns:
            Vote with direction, confidence, and detailed reasoning
        """
        # Step 1: Run local OpenClaw board analysis
        board_decision = self._analyze_with_board(market, position_state)

        # Step 2: Optionally enhance with Groq-powered sentiment analysis
        groq_enhancement = None
        if self._client and config.OPENCLAW_ENABLED:
            groq_enhancement = self._enhance_with_groq(
                market, prior_votes, board_decision, position_state
            )

        # Step 3: Synthesize final vote from board decision + optional Groq enhancement
        final_vote = self._synthesize_final_vote(
            board_decision, groq_enhancement, prior_votes
        )

        self._last_decision = {
            "board_decision": board_decision,
            "groq_enhancement": groq_enhancement,
            "final_vote": {
                "direction": final_vote.direction.value,
                "confidence": final_vote.confidence,
                "reasoning": final_vote.reasoning,
            }
        }

        return final_vote

    def _analyze_with_board(
        self, market: MarketData, position_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run the local OpenClaw board analysis with available market signals.
        This doesn't require API calls — it's pure Python logic.
        """
        try:
            # Extract key metrics from market data
            rsi = market.rsi_14 if hasattr(market, "rsi_14") else 50.0
            macd_status = self._get_macd_status(market)
            price_change_1h = market.change_1h_pct if hasattr(market, "change_1h_pct") else 0.0
            current_leverage = position_state.get("current_leverage", 1.0)
            portfolio_drawdown = position_state.get("portfolio_drawdown_pct", 0.0)

            # Social sentiment (defaults if not available)
            reddit_mentions = position_state.get("reddit_mentions", 50)
            reddit_sentiment = position_state.get("reddit_sentiment_pct", 50.0)
            reddit_themes = position_state.get("reddit_themes", [])
            news_sentiment = position_state.get("news_sentiment_pct", 50.0)
            news_headlines = position_state.get("news_headlines", [])

            # Run board decision
            board_decision = self._board.analyze_signal(
                ticker=market.pair,
                price_change_1h=price_change_1h,
                rsi=rsi,
                macd_status=macd_status,
                current_leverage=current_leverage,
                portfolio_drawdown=portfolio_drawdown,
                reddit_mentions=reddit_mentions,
                reddit_sentiment=reddit_sentiment,
                reddit_themes=reddit_themes,
                news_sentiment=news_sentiment,
                news_headlines=news_headlines,
            )

            return board_decision.__dict__ if hasattr(board_decision, "__dict__") else {}

        except Exception as e:
            logger.warning(f"[dim]Board analysis error: {e}[/dim]")
            return {}

    def _get_macd_status(self, market: MarketData) -> str:
        """Determine MACD status from market data"""
        if hasattr(market, "macd_signal") and hasattr(market, "macd_value"):
            if market.macd_value > market.macd_signal:
                return "bullish_cross"
            else:
                return "bearish_cross"
        return "neutral"

    def _enhance_with_groq(
        self,
        market: MarketData,
        prior_votes: List[Vote],
        board_decision: Dict[str, Any],
        position_state: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Call Groq Llama 3.3 70B for advanced sentiment analysis and web context.
        This enhances the board decision with LLM reasoning.
        """
        if not self._client:
            return None

        try:
            prompt = self._build_groq_prompt(
                market, prior_votes, board_decision, position_state
            )

            start_time = time.time()
            response = self._client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,  # Deterministic, auditable
                max_tokens=500,
                timeout=self._timeout,
            )
            elapsed = time.time() - start_time
            logger.debug(f"[dim]Groq response in {elapsed:.2f}s[/dim]")

            response_text = response.choices[0].message.content if response.choices else ""
            parsed = self._parse_groq_response(response_text)

            return parsed if parsed else None

        except Exception as e:
            logger.warning(f"[dim]Groq enhancement error: {e}[/dim]")
            return None

    def _build_groq_prompt(
        self,
        market: MarketData,
        prior_votes: List[Vote],
        board_decision: Dict[str, Any],
        position_state: Dict[str, Any],
    ) -> str:
        """Build the Groq prompt for LLM-powered sentiment analysis"""
        votes_text = "\n".join([
            f"- {v.agent_id}: {v.direction.value} ({v.confidence:.1%})"
            for v in prior_votes
        ])

        prompt = f"""You are analyzing a cryptocurrency trade decision for {market.pair} at ${market.current_price:,.2f}.

## Board Decision (Local Analysis)
{board_decision.get('execution_packet', 'N/A')}

## Agent Votes
{votes_text}

## Current Risk
- Portfolio drawdown: {position_state.get('portfolio_drawdown_pct', 0):.1f}%
- Current leverage: {position_state.get('current_leverage', 1.0):.1f}x

## Your Task
1. Assess whether the board decision is sound given market conditions
2. Identify any red flags or opportunities
3. Return a JSON enhancement with sentiment_boost, risk_adjustment, and enhanced_rationale

Respond with ONLY valid JSON (no markdown):
{{
  "sentiment_boost": <-0.2 to +0.2 adjustment>,
  "risk_adjustment": <"high" | "medium" | "low">,
  "enhanced_rationale": "<2-3 sentences explaining the sentiment picture>",
  "web_context": "<any notable market sentiment signals>"
}}"""
        return prompt

    def _parse_groq_response(self, response_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from Groq"""
        response_text = response_text.strip()

        # Extract JSON if wrapped in markdown
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end > start:
                response_text = response_text[start:end].strip()

        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.debug(f"[dim]Failed to parse Groq response: {response_text[:100]}[/dim]")
            return None

    def _synthesize_final_vote(
        self,
        board_decision: Dict[str, Any],
        groq_enhancement: Optional[Dict[str, Any]],
        prior_votes: List[Vote],
    ) -> Vote:
        """
        Combine board decision + optional Groq enhancement into final vote.
        """
        # Base from board
        board_vote_str = board_decision.get("board_vote", "HOLD")
        if isinstance(board_vote_str, str):
            board_vote = board_vote_str
        else:
            board_vote = str(board_vote_str).split(".")[-1] if hasattr(board_vote_str, "value") else "HOLD"

        board_leverage = board_decision.get("leverage", 1.0)
        board_rationale = board_decision.get("rationale", "Board decision")

        # Adjust with Groq if available
        confidence = 0.65 + (board_leverage - 1.0) * 0.1
        rationale = board_rationale

        if groq_enhancement:
            sentiment_boost = groq_enhancement.get("sentiment_boost", 0.0)
            confidence = min(0.95, max(0.05, confidence + sentiment_boost))
            rationale = groq_enhancement.get(
                "enhanced_rationale", rationale
            )

        # Ensure valid direction
        if board_vote not in ("BUY", "SELL", "HOLD"):
            board_vote = "HOLD"

        return Vote(
            agent_id=self.agent_id,
            direction=VoteDirection(board_vote),
            confidence=confidence,
            reasoning=f"OpenClaw Board ({board_decision.get('consensus_level', '?')}): {rationale[:100]}",
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
