"""
NEXUS Consensus Engine — reputation-weighted voting with PnL-proportional learning.
Includes strategy weight modifiers, LLM adjudication, and YOLO activation gating.
"""
import json
import logging
import math
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any

import config

logger = logging.getLogger(__name__)

# Strategy-specific agent weight modifiers (Section 6E)
STRATEGY_MODIFIERS = {
    "trend_following": {
        "momentum": 1.5,
        "sentiment": 0.8,
    },
    "breakout": {
        "orderflow": 1.8,
        "momentum": 1.3,
    },
    "mean_reversion": {
        "sentiment": 1.4,
        "momentum": 1.2,  # Inverted signal
    },
    "scalping": {
        "risk_guardian": 2.0,
    },
    "swing": {
        "llm_reasoner": 2.5,
    },
    "smc": {
        "llm_reasoner": 2.0,
        "orderflow": 1.5,
    },
    "position": {
        "llm_reasoner": 3.0,
        "sentiment": 1.5,
    },
    "arbitrage": {
        "orderflow": 2.0,
    },
    # trend_following, breakout, algorithmic_quant (default) use default weights
    # yolo handled separately with gating
}

# NEW: Default agent base weights (applied to all strategies)
# CORRECTED: Weights based on ACTUAL PERFORMANCE, not theoretical roles
# Performance data: Sentiment +$120.62 (best), Risk Guardian +$37.70, 
# Mean Reversion +$15.41, Momentum -$25.74 (losing), OrderFlow -$144.74 (worst)
AGENT_BASE_WEIGHTS = {
    "sentiment": 1.8,          # HIGHEST: Only profitable agent (+$120.62)
    "risk_guardian": 1.6,      # HIGH: Positive PnL (+$37.70)
    "mean_reversion": 1.0,     # NEUTRAL: Barely positive (+$15.41), 0% win rate
    "momentum": 0.8,           # REDUCED: Losing agent (-$25.74)
    "orderflow": 0.5,          # LOWEST: Worst performer (-$144.74)
    "llm_reasoner": 2.0,       # LLM adjudication
    "yolo": 1.0,               # Extreme bullish
}


@dataclass
class AgentRecord:
    """Reputation record for a single agent."""
    agent_id: str
    weight: float = config.INITIAL_AGENT_WEIGHT
    trades_closed: int = 0
    pnl_total: float = 0.0
    wins: int = 0
    losses: int = 0
    retired: bool = False
    consecutive_floor_trades: int = 0

    # Rolling accuracy window (last 20 trades)
    recent_outcomes: deque = field(default_factory=lambda: deque(maxlen=config.ROLLING_ACCURACY_WINDOW))

    def accuracy_pct(self) -> float:
        """Accuracy in rolling window (0–100%)."""
        if len(self.recent_outcomes) == 0:
            return 0.0
        return (sum(self.recent_outcomes) / len(self.recent_outcomes)) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON storage."""
        return {
            "agent_id": self.agent_id,
            "weight": self.weight,
            "trades_closed": self.trades_closed,
            "pnl_total": self.pnl_total,
            "wins": self.wins,
            "losses": self.losses,
            "retired": self.retired,
            "consecutive_floor_trades": self.consecutive_floor_trades,
        }


class ConsensusEngine:
    """Reputation-weighted consensus with PnL-proportional learning."""

    def __init__(self):
        self.records: Dict[str, AgentRecord] = {}
        self.hold_log: List[Dict] = []
        self.hold_log_timestamps: Dict[int, Dict] = {}  # For counterfactual tracking
        self.load_weights()

    def load_weights(self):
        """Load agent weights from nexus_weights.json."""
        try:
            with open(config.WEIGHTS_FILE, "r") as f:
                data = json.load(f)
                for record_data in data:
                    rec = AgentRecord(
                        agent_id=record_data["agent_id"],
                        weight=record_data.get("weight", config.INITIAL_AGENT_WEIGHT),
                        trades_closed=record_data.get("trades_closed", 0),
                        pnl_total=record_data.get("pnl_total", 0.0),
                        wins=record_data.get("wins", 0),
                        losses=record_data.get("losses", 0),
                        retired=record_data.get("retired", False),
                        consecutive_floor_trades=record_data.get("consecutive_floor_trades", 0),
                    )
                    self.records[rec.agent_id] = rec
            logger.info(f"[green]Loaded weights for {len(self.records)} agents[/green]")
        except FileNotFoundError:
            logger.info("[dim]No existing weights file; starting fresh[/dim]")

    def save_weights(self):
        """Persist agent weights to nexus_weights.json."""
        try:
            data = [rec.to_dict() for rec in self.records.values()]
            with open(config.WEIGHTS_FILE, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"[red]Failed to save weights: {e}[/red]")

    def register_agent(self, agent_id: str):
        """Register a new agent with base weight from AGENT_BASE_WEIGHTS."""
        if agent_id not in self.records:
            # Use agent-specific base weight if available, otherwise use default
            base_weight = AGENT_BASE_WEIGHTS.get(agent_id, config.INITIAL_AGENT_WEIGHT)
            self.records[agent_id] = AgentRecord(
                agent_id=agent_id,
                weight=base_weight,
            )

    def _get_strategy_modifier(self, agent_id: str, strategy: str) -> float:
        """Get weight modifier for agent in specific strategy (default 1.0)."""
        if strategy not in STRATEGY_MODIFIERS:
            return 1.0
        modifiers = STRATEGY_MODIFIERS[strategy]
        return modifiers.get(agent_id, 1.0)

    def vote(self, votes: List, strategy: str = None, market_data = None) -> tuple:
        """
        Compute consensus from agent votes with strategy-specific weight modifiers.
        
        Process:
        1. Filter standard agents (exclude LLM/YOLO)
        2. Apply strategy weight modifiers to standard agents
        3. Compute consensus from standard agents
        4. Inject LLMReasonerAgent vote if available (weight 2.0, post-consensus adjudication)
        5. Gate YOLO activation if conditions met (replace consensus or supplement)
        
        Args:
            votes: List of Vote objects (all agents)
            strategy: Strategy name to apply weight modifiers (e.g., "trend_following")
            market_data: MarketData object for YOLO activation checks
            
        Returns:
            (consensus_direction, consensus_confidence, all_votes, llm_rationale)
        """
        if not votes:
            logger.error("[red]No votes provided to consensus engine[/red]")
            from agents.base import VoteDirection, Vote
            return VoteDirection.HOLD, 0.0, [], None

        if strategy is None:
            strategy = config.ACTIVE_STRATEGY

        # Ensure all voting agents are registered
        for vote in votes:
            self.register_agent(vote.agent_id)

        # Separate standard agents from LLM/YOLO
        from agents.base import VoteDirection
        
        standard_votes = [v for v in votes if v.agent_id not in ["llm_reasoner", "yolo"]]
        llm_votes = [v for v in votes if v.agent_id == "llm_reasoner"]
        yolo_votes = [v for v in votes if v.agent_id == "yolo"]

        # Filter retired agents from standard votes only
        active_standard_votes = [v for v in standard_votes if not self.records[v.agent_id].retired]

        if not active_standard_votes:
            logger.warning("[yellow]All standard agents retired; cannot vote[/yellow]")
            return VoteDirection.HOLD, 0.0, votes, None

        # Compute weighted scores with strategy modifiers + ACCURACY-BASED WEIGHTING
        buy_score = 0.0
        sell_score = 0.0
        total_weight = 0.0
        
        # Track agents for highest accuracy override
        agent_performances = []

        for vote in active_standard_votes:
            record = self.records[vote.agent_id]
            base_weight = record.weight
            strategy_modifier = self._get_strategy_modifier(vote.agent_id, strategy)
            
            # NEW: Apply accuracy-based multiplier (AGGRESSIVE VERSION)
            # Punish terrible agents much more than before
            # Examples: 16% accuracy → 0.32x, 42% accuracy → 0.84x, 80% accuracy → 1.6x
            accuracy_pct = record.accuracy_pct()  # 0-100%
            
            # AGGRESSIVE formula: max(0.2, min(1.5, accuracy / 50))
            # This heavily punishes agents with <50% win rate (below baseline)
            accuracy_multiplier = max(0.2, min(1.5, accuracy_pct / 50.0))
            
            logger.debug(f"[dim]{vote.agent_id}: accuracy={accuracy_pct:.1f}% → multiplier={accuracy_multiplier:.2f}x[/dim]")
            
            effective_weight = base_weight * strategy_modifier * accuracy_multiplier

            if vote.direction.value == "BUY":
                buy_score += effective_weight * vote.confidence
            elif vote.direction.value == "SELL":
                sell_score += effective_weight * vote.confidence

            total_weight += effective_weight
            
            # Track for override logic
            agent_performances.append({
                "agent_id": vote.agent_id,
                "accuracy": accuracy_pct,
                "pnl": record.pnl_total,
                "direction": vote.direction.value,
                "confidence": vote.confidence,
                "effective_weight": effective_weight,
            })

        # Normalize
        if total_weight > 0:
            buy_score /= total_weight
            sell_score /= total_weight

        # Determine consensus from standard agents
        if buy_score > config.CONFIDENCE_THRESHOLD and buy_score > sell_score:
            consensus_direction = VoteDirection.BUY
            consensus_confidence = buy_score
        elif sell_score > config.CONFIDENCE_THRESHOLD and sell_score > buy_score:
            consensus_direction = VoteDirection.SELL
            consensus_confidence = sell_score
        else:
            consensus_direction = VoteDirection.HOLD
            consensus_confidence = max(buy_score, sell_score)

        logger.debug(
            f"[dim]Standard agents consensus: {consensus_direction.value} "
            f"(buy={buy_score:.3f}, sell={sell_score:.3f}, strategy={strategy})[/dim]"
        )

        # NEW: HIGHEST ACCURACY OVERRIDE
        # If any agent has >70% accuracy and positive PnL, give them override voting power
        if agent_performances:
            agent_performances.sort(key=lambda x: (x["accuracy"], x["pnl"]), reverse=True)
            top_agent = agent_performances[0]
            
            if top_agent["accuracy"] >= 70.0 and top_agent["pnl"] > 0:
                # Top agent can override if their confidence is high
                if top_agent["confidence"] >= 0.60:
                    override_influence = 0.25  # 25% override influence from best agent
                    old_direction = consensus_direction
                    old_confidence = consensus_confidence
                    
                    if top_agent["direction"] == "BUY":
                        consensus_direction = VoteDirection.BUY
                        consensus_confidence = consensus_confidence * (1 - override_influence) + override_influence
                    elif top_agent["direction"] == "SELL":
                        consensus_direction = VoteDirection.SELL
                        consensus_confidence = consensus_confidence * (1 - override_influence) + override_influence
                    
                    logger.info(
                        f"[cyan]🏆 ACCURACY OVERRIDE: Agent '{top_agent['agent_id']}' "
                        f"(acc={top_agent['accuracy']:.1f}%, pnl=${top_agent['pnl']:.2f}) "
                        f"overrides consensus: {old_direction.value} → {consensus_direction.value} "
                        f"(conf {old_confidence:.3f} → {consensus_confidence:.3f})[/cyan]"
                    )

        # Inject LLMReasonerAgent vote if available (post-consensus adjudication with weight 2.0)
        llm_rationale = None
        if llm_votes:
            llm_vote = llm_votes[0]
            self.register_agent("llm_reasoner")
            llm_record = self.records["llm_reasoner"]
            llm_modifier = self._get_strategy_modifier("llm_reasoner", strategy)
            llm_weight = llm_record.weight * llm_modifier
            
            # Extract rationale if available
            if hasattr(llm_vote, 'metadata') and llm_vote.metadata:
                llm_rationale = llm_vote.metadata.get('rationale', None)
            
            # Apply LLM vote as adjudication (override or reinforce)
            llm_adjustment = 0.15 * llm_weight  # 15% influence from LLM
            if llm_vote.direction.value == "BUY":
                consensus_confidence += llm_adjustment * llm_vote.confidence
            elif llm_vote.direction.value == "SELL":
                consensus_confidence -= llm_adjustment * llm_vote.confidence
            # HOLD votes don't adjust confidence
            
            # Clamp confidence to 0-1
            consensus_confidence = max(0.0, min(1.0, consensus_confidence))
            
            logger.debug(
                f"[cyan]LLM adjudication: +{llm_adjustment:.3f} confidence "
                f"({llm_vote.direction.value}, conf={llm_vote.confidence:.2f})[/cyan]"
            )

        # Gate YOLO activation if conditions met
        yolo_is_active = False
        if yolo_votes and config.YOLO_ENABLED:
            yolo_vote = yolo_votes[0]
            # Check if YOLO agent is activation condition met (happens in agents/yolo.py)
            if yolo_vote.direction.value == "BUY" and yolo_vote.confidence > 0.8:
                yolo_is_active = True
                self.register_agent("yolo")
                yolo_record = self.records["yolo"]
                yolo_modifier = self._get_strategy_modifier("yolo", strategy)
                yolo_weight = yolo_record.weight * yolo_modifier
                
                # YOLO overrides consensus with extreme confidence
                consensus_direction = VoteDirection.BUY
                consensus_confidence = min(1.0, 0.95)  # Max 95% confidence
                
                logger.warning(
                    f"[yellow]🎲 YOLO ACTIVATION: Extreme bullish override (weight={yolo_weight:.2f})[/yellow]"
                )

        # Return all votes for audit trail
        all_votes = active_standard_votes + (llm_votes if llm_votes else []) + (yolo_votes if yolo_votes else [])
        
        return consensus_direction, consensus_confidence, all_votes, llm_rationale

    def record_hold(self, market_data, votes: List, current_price: float):
        """
        Record a HOLD decision for counterfactual analysis.
        After 12 cycles (~1 hour), check what the PnL would have been.
        """
        timestamp = int(time.time())
        self.hold_log_timestamps[timestamp] = {
            "price": current_price,
            "agent_votes": [
                {
                    "agent_id": v.agent_id,
                    "direction": v.direction.value,
                    "confidence": v.confidence,
                }
                for v in votes
            ],
        }

        # Check for counterfactuals (12 cycles later = ~60 minutes)
        cutoff = timestamp - (12 * config.LOOP_INTERVAL_SECONDS)
        for old_timestamp in list(self.hold_log_timestamps.keys()):
            if old_timestamp < cutoff:
                old_entry = self.hold_log_timestamps[old_timestamp]
                old_price = old_entry["price"]
                price_change = current_price - old_price
                pnl_usd = price_change  # Simplified; assumes 1 unit

                # Determine majority direction
                buy_count = sum(
                    1 for v in old_entry["agent_votes"] if v["direction"] == "BUY"
                )
                sell_count = sum(
                    1 for v in old_entry["agent_votes"] if v["direction"] == "SELL"
                )
                majority_dir = "BUY" if buy_count > sell_count else "SELL"

                if price_change > 0 and majority_dir == "BUY":
                    logger.debug(
                        f"[dim]Counterfactual HOLD: would have been +${pnl_usd:.2f} "
                        f"if {majority_dir}[/dim]"
                    )
                elif price_change < 0 and majority_dir == "SELL":
                    logger.debug(
                        f"[dim]Counterfactual HOLD: would have been +${abs(pnl_usd):.2f} "
                        f"if {majority_dir}[/dim]"
                    )

                del self.hold_log_timestamps[old_timestamp]

    def record_outcome(
        self,
        direction_str: str,
        confidence: float,
        votes: List,
        pnl_usd: float,
        current_price: float,
    ):
        """
        Record a closed trade and update agent weights via PnL-proportional learning.

        Args:
            direction_str: "BUY" or "SELL" (the direction that was executed)
            confidence: consensus confidence from vote()
            votes: list of Vote objects
            pnl_usd: profit/loss in USD
            current_price: current price at close
        """
        # Determine winners and losers
        from agents.base import VoteDirection

        direction_enum = VoteDirection(direction_str)
        winners = [v for v in votes if v.direction == direction_enum]
        losers = [v for v in votes if v.direction != direction_enum]

        # Update records
        for vote in votes:
            if vote.agent_id not in self.records:
                self.register_agent(vote.agent_id)

            record = self.records[vote.agent_id]
            record.trades_closed += 1

            is_win = vote in winners and pnl_usd >= 0
            record.recent_outcomes.append(1 if is_win else 0)

            if pnl_usd >= 0:
                # Profitable trade
                if vote in winners:
                    # Agent was correct
                    self._boost(record, vote.confidence, pnl_usd)
                    record.wins += 1
                    record.pnl_total += pnl_usd
                    logger.debug(
                        f"[green]Agent {vote.agent_id} boosted +${pnl_usd:.2f} "
                        f"(weight={record.weight:.2f})[/green]"
                    )
                else:
                    # Agent dissented (loss avoidance credit)
                    self._boost(record, 0.3 * vote.confidence, pnl_usd)
                    record.pnl_total += pnl_usd * 0.1  # Partial credit
                    logger.debug(f"[dim]Agent {vote.agent_id} dissent credit +${pnl_usd * 0.1:.2f}[/dim]")
            else:
                # Loss
                if vote in losers:
                    # Agent was wrong
                    self._penalise(record, vote.confidence, pnl_usd)
                    record.losses += 1
                    record.pnl_total += pnl_usd
                    logger.debug(
                        f"[red]Agent {vote.agent_id} penalised ${pnl_usd:.2f} "
                        f"(weight={record.weight:.2f})[/red]"
                    )
                else:
                    # Agent dissented (loss avoidance credit)
                    self._boost(record, 0.3 * vote.confidence, abs(pnl_usd))
                    record.pnl_total += abs(pnl_usd) * 0.1
                    logger.debug(f"[dim]Agent {vote.agent_id} dissent credit +${abs(pnl_usd) * 0.1:.2f}[/dim]")

            # Check for retirement (weight at floor for 10 consecutive trades)
            if record.weight <= 0.15:
                record.consecutive_floor_trades += 1
                if record.consecutive_floor_trades >= config.AGENT_RETIREMENT_FLOOR_TRADES:
                    record.retired = True
                    logger.warning(
                        f"[yellow]Agent {vote.agent_id} retired — "
                        f"weight at floor for {config.AGENT_RETIREMENT_FLOOR_TRADES} trades[/yellow]"
                    )
            else:
                record.consecutive_floor_trades = 0

        self.save_weights()

    def _boost(self, record: AgentRecord, confidence: float, pnl_usd: float):
        """Boost agent weight for correct/dissenting vote."""
        magnitude = math.tanh(abs(pnl_usd) / max(config.MAX_TRADE_SIZE_USD, 1.0))
        delta = config.WEIGHT_LEARN_RATE * confidence * magnitude
        record.weight = max(0.1, min(5.0, record.weight + delta))

    def _penalise(self, record: AgentRecord, confidence: float, pnl_usd: float):
        """Penalise agent weight for incorrect vote."""
        magnitude = math.tanh(abs(pnl_usd) / max(config.MAX_TRADE_SIZE_USD, 1.0))
        delta = config.WEIGHT_LEARN_RATE * confidence * magnitude
        record.weight = max(0.1, min(5.0, record.weight - delta))

    def leaderboard(self) -> str:
        """Generate leaderboard string."""
        if not self.records:
            return "[dim]No agent records yet[/dim]"

        lines = ["NEXUS Agent Leaderboard (rolling 20-trade window):", ""]
        for agent_id, record in sorted(self.records.items(), key=lambda x: -x[1].pnl_total):
            retired_marker = " [RETIRED]" if record.retired else ""
            lines.append(
                f"  {agent_id:20} | Weight: {record.weight:5.2f} | "
                f"Accuracy: {record.accuracy_pct():5.1f}% | "
                f"PnL: ${record.pnl_total:8.2f} | "
                f"W/L: {record.wins}/{record.losses}{retired_marker}"
            )
        return "\n".join(lines)
