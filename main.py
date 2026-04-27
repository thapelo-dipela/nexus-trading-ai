"""
NEXUS Main Orchestration Loop — CLI and trading engine.
"""
import warnings
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)

import sys
import time
import argparse
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple

from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler

import config
from agents import create_default_agents
from agents.base import MarketData, Candle, PrismSignal, PrismRisk, VoteDirection
from consensus.engine import ConsensusEngine
from consensus.regime import RegimeDetector, MarketRegime
from data.prism import PrismClient
from data.stock_market import StockMarketClient
from execution.alpaca_client import AlpacaClient
from execution.kraken import KrakenClient
from execution import compute_position_size
from execution.positions import PositionManager, ExitReason
from execution.sandbox_capital import SandboxCapitalManager, CapitalAllocationManager
from onchain.reputation import ReputationClient
from compliance import ComplianceEngine
from validation import ValidationEngine
import importlib
yield_module = importlib.import_module("yield")
YieldOptimizer = yield_module.YieldOptimizer
from agents.mean_reversion import MeanReversionAgent
from agents.payer_agent import PayerAgent
from agents.receiver_agent import ReceiverAgent
from execution.leaderboard import LeaderboardManager
import requests

# Setup logging with rich
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(show_time=False, show_level=False, show_path=False)],
)
logger = logging.getLogger("nexus")


def setup_logging(verbose: bool):
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)


def save_live_decisions(cycle_num, agent_decisions, consensus_direction, consensus_confidence, positions, recent_closes):
    """Save live decisions to JSON for dashboard display"""
    try:
        data = {
            'latest_cycle': cycle_num,
            'agent_decisions': agent_decisions,
            'consensus_decision': {
                'direction': consensus_direction.value if consensus_direction else 'HOLD',
                'confidence': float(consensus_confidence),
            },
            'positions': positions,
            'recent_closes': recent_closes,
            'timestamp': datetime.now().isoformat()
        }
        with open('nexus_live_decisions.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to save live decisions: {e}")


def save_cycle_log(cycle_num, consensus_direction, consensus_confidence, llm_rationale="", orderflow_metrics=None, signed_votes=None, strategy="", stock_signal=None):
    """
    Save cycle data to nexus_cycle_log.json for dashboard audit trail.
    Includes LLM rationale, strategy, and signed vote audit log.
    """
    try:
        cycle_entry = {
            "cycle_number": cycle_num,
            "timestamp": int(time.time()),
            "consensus_direction": consensus_direction.value if consensus_direction else "HOLD",
            "consensus_confidence": float(consensus_confidence),
            "strategy": strategy or config.ACTIVE_STRATEGY,
            "stock_signal": stock_signal or {},
            "llm_rationale": llm_rationale or "",
            "orderflow": orderflow_metrics or {},
            "signed_votes": signed_votes or [],
        }
        
        # Try to append to existing cycle log or create new
        existing = []
        try:
            with open(config.CYCLE_LOG_FILE, 'r') as f:
                data = json.load(f)
                existing = data if isinstance(data, list) else []
        except (FileNotFoundError, json.JSONDecodeError):
            existing = []
        
        # Keep last 100 cycles
        existing.append(cycle_entry)
        existing = existing[-100:]
        
        with open(config.CYCLE_LOG_FILE, 'w') as f:
            json.dump(existing, f, indent=2)
    except Exception as e:
        logger.debug(f"Failed to save cycle log: {e}")


# ─── Connectivity Check ───────────────────────────────────────────────────────

def ping_prism_and_kraken(prism_client: PrismClient, kraken_client: KrakenClient) -> bool:
    """
    Test only endpoints that actually exist and work.
    Tests confirmed working endpoints based on live API responses.
    """
    try:
        console.print("\n[bold]NEXUS --ping: Connectivity Check[/bold]")

        # Test 1: PRISM /resolve/BTC
        console.print(f"Testing PRISM /resolve/{config.PRISM_SYMBOL}...", end=" ")
        resolved = prism_client.resolve_asset(config.PRISM_SYMBOL)
        if resolved and resolved.get("symbol") == config.PRISM_SYMBOL:
            console.print("[green]✓[/green]")
        else:
            console.print("[red]✗[/red]")
            return False

        # Test 2: Get price from /signals/{symbol}
        # NOTE: /crypto/{symbol}/price does NOT exist, price comes from /signals
        console.print(f"Testing PRISM /signals/{config.PRISM_SYMBOL} (price extraction)...", end=" ")
        price_result = prism_client.get_price(config.PRISM_SYMBOL)
        if price_result and "price" in price_result and price_result["price"] > 0:
            current_price = float(price_result["price"])
            console.print(f"[green]✓[/green] (${current_price:,.2f})")
        else:
            console.print("[red]✗[/red]")
            return False

        # Test 3: Get 1h signal
        console.print(f"Testing PRISM /signals/{config.PRISM_SYMBOL} (1h)...", end=" ")
        signal_1h = prism_client.get_signals(config.PRISM_SYMBOL, timeframe="1h")
        if signal_1h and signal_1h.current_price > 0:
            console.print(
                f"[green]✓[/green] ({signal_1h.direction} rsi={signal_1h.rsi:.1f})"
            )
        else:
            console.print("[red]✗[/red]")
            return False

        # Test 4: Get 4h signal
        console.print(f"Testing PRISM /signals/{config.PRISM_SYMBOL} (4h)...", end=" ")
        signal_4h = prism_client.get_signals(config.PRISM_SYMBOL, timeframe="4h")
        if signal_4h and signal_4h.current_price > 0:
            console.print(
                f"[green]✓[/green] ({signal_4h.direction} conf={signal_4h.confidence:.2f})"
            )
        else:
            console.print("[red]✗[/red]")
            return False

        # Test 5: Get risk
        console.print(f"Testing PRISM /risk/{config.PRISM_SYMBOL}...", end=" ")
        risk = prism_client.get_risk(config.PRISM_SYMBOL)
        if risk and risk.sharpe_ratio is not None:
            console.print(f"[green]✓[/green] (risk_score={risk.risk_score:.1f} sharpe={risk.sharpe_ratio:.2f})")
        else:
            console.print(f"[yellow]⚠ timed out — agent will use local ATR fallback[/yellow]")

        # Test 6: Kraken balance
        console.print(f"Testing Kraken balance -o json...", end=" ")
        portfolio_value, open_position = kraken_client.portfolio_summary()
        if portfolio_value >= 0:
            console.print(
                f"[green]✓[/green] (${portfolio_value:,.2f})"
            )
        else:
            console.print("[red]✗[/red]")
            return False

        # Test 7: Kraken ticker
        console.print(f"Testing Kraken ticker -o json {config.PAIR}...", end=" ")
        ticker_price = kraken_client.get_ticker_price()
        if ticker_price and ticker_price > 0:
            console.print(f"[green]✓[/green] (${ticker_price:,.2f})")
        else:
            console.print("[red]✗[/red]")
            return False

        console.print("\n[bold green]All connectivity checks passed![/bold green]")
        return True

    except Exception as e:
        console.print(f"\n[red]Connectivity check failed: {e}[/red]")
        return False


def trade_cycle(
    market_data: MarketData,
    agents: list,
    consensus_engine: ConsensusEngine,
    kraken_client: KrakenClient,
    reputation_client: ReputationClient,
    compliance_engine: ComplianceEngine,
    validation_engine: ValidationEngine,
    yield_optimizer: YieldOptimizer,
    position_manager: PositionManager,
    regime_detector: RegimeDetector,
    cycle_number: int = 0,
    dry_run: bool = False,
    btc_signal=None,
    alpaca_client=None,
    stock_market=None,
) -> bool:
    """
    Execute a single trade cycle with comprehensive compliance and validation:
    1. Check open positions for exits (stop-loss, take-profit, time-based)
    2. If positions close, record outcome and update agent weights
    3. Detect market regime and adjust agent weights
    4. Collect agent votes
    5. Compute consensus with regime-adjusted weights
    6. Size position
    7. Run compliance checks (hackathon standards)
    8. Create trust markers (trustless verification)
    9. Execute trade (or log dry-run)
    10. Push outcome to on-chain reputation registry
    """
    timestamp = int(time.time())

    # ============ STEP 1: Check open positions for exits ============
    if position_manager.has_open_position():
        # check_exits returns a list of Position objects that hit SL/TP/time limits
        positions_to_close = position_manager.check_exits(market_data.current_price)
        for position in positions_to_close:
            exit_price = market_data.current_price
            # Determine exit reason for logging
            upnl_pct = position.unrealised_pnl_pct(exit_price)
            if upnl_pct >= config.TAKE_PROFIT_PCT:
                exit_reason = ExitReason.TAKE_PROFIT
            elif upnl_pct <= -config.STOP_LOSS_PCT:
                exit_reason = ExitReason.STOP_LOSS
            else:
                exit_reason = ExitReason.TIME_BASED

            logger.info(
                f"[bold red]EXIT {position.direction}[/bold red] "
                f"at ${exit_price:.2f} ({exit_reason.value})"
            )
            closed = position_manager.close_position(
                position.trade_id, exit_price, exit_reason.value
            )
            pnl_usd = closed.pnl_usd if closed else 0.0
            logger.info(f"[bold green]PnL: ${pnl_usd:.2f}[/bold green]")

            # ============ TRAINING STEP — update agent weights from this trade outcome ============
            current_votes = []
            for agent in agents:
                try:
                    vote = agent.analyze(market_data)
                    if vote:
                        current_votes.append(vote)
                except Exception:
                    pass

            if current_votes:
                consensus_engine.record_outcome(
                    direction_str=position.direction,
                    confidence=position.entry_confidence,
                    votes=current_votes,
                    pnl_usd=pnl_usd,
                    current_price=market_data.current_price,
                )
                logger.info(
                    f"[bold cyan]Weights updated[/bold cyan] — "
                    f"{'win' if pnl_usd >= 0 else 'loss'} ${pnl_usd:+.2f} "
                    f"across {len(current_votes)} agents"
                )

            # Record outcome on-chain — votes now captured above
            signed_outcome = reputation_client.sign_trade_outcome(
                trade_id=position.trade_id,
                direction=position.direction,
                confidence=position.entry_confidence,
                pnl_usd=pnl_usd,
                agent_votes={v.agent_id: v.direction.value for v in current_votes},
            )
            if signed_outcome:
                reputation_client.push_outcome(signed_outcome, dry_run=False)
        if positions_to_close:
            return True

    # Initialize risk_adj_score (placeholder for now)
    risk_adj_score = 0.0

    # ============ STEP 2: Detect market regime and adjust agent weights ============
    regime = regime_detector.detect_regime(market_data)
    regime_weights = regime_detector.get_agent_weights(regime)
    logger.info(f"[bold blue]Market Regime[/bold blue]: {regime.value} | Weights: {regime_weights}")

    # ============ STEP 3: Collect agent votes ============
    votes = []
    agent_decisions = []
    
    # Standard agents (all except llm_reasoner)
    standard_agents = [a for a in agents if a.agent_id != "llm_reasoner"]
    llm_agent = next((a for a in agents if a.agent_id == "llm_reasoner"), None)
    
    for agent in standard_agents:
        vote = agent.analyze(market_data)
        if vote:
            votes.append(vote)
            regime_mult = regime_weights.get(agent.agent_id, 1.0)
            logger.info(
                f"  {agent.agent_id}: {vote.direction.value} "
                f"(conf={vote.confidence:.2f}, regime_mult={regime_mult})"
            )
            # Store decision for dashboard
            agent_decisions.append({
                'agent_id': agent.agent_id,
                'direction': vote.direction.value,
                'confidence': float(vote.confidence),
                'regime_multiplier': regime_mult,
                'reasoning': getattr(vote, 'reasoning', 'Analysis complete')
            })

    if not votes:
        logger.warning("[yellow]No valid votes from standard agents[/yellow]")
        return True

    # ============ STEP 3b: LLM Reasoner adjudication (optional) ============
    if llm_agent:
        try:
            position_state = {
                "portfolio_value_usd": float(market_data.portfolio_value_usd),
                "open_position_usd": float(market_data.open_position_usd),
                "cash_available": float(market_data.cash_usd),
            }
            llm_vote = llm_agent.vote_with_context(
                market=market_data,
                prior_votes=votes,
                position_state=position_state,
            )
            if llm_vote:
                votes.append(llm_vote)
                logger.info(
                    f"  {llm_agent.agent_id}: {llm_vote.direction.value} "
                    f"(conf={llm_vote.confidence:.2f}) [LLM ADJUDICATION]"
                )
                agent_decisions.append({
                    'agent_id': llm_agent.agent_id,
                    'direction': llm_vote.direction.value,
                    'confidence': float(llm_vote.confidence),
                    'regime_multiplier': regime_weights.get(llm_agent.agent_id, 2.0),
                    'reasoning': llm_vote.reasoning
                })
        except Exception as e:
            logger.warning(f"[yellow]LLM reasoning failed: {e}[/yellow]")
            # Continue without LLM vote

    # ============ STEP 4: Compute consensus (strategy-weighted, LLM adjudicated) ============
    active_strategy = config.ACTIVE_STRATEGY
    consensus_direction, consensus_confidence, active_votes, llm_rationale_from_engine = consensus_engine.vote(
        votes, 
        strategy=active_strategy,
        market_data=market_data
    )

    # Extract LLM rationale (prefer from engine, fallback to direct agent)
    llm_rationale = llm_rationale_from_engine or ""
    if not llm_rationale and llm_agent and hasattr(llm_agent, '_last_rationale'):
        llm_rationale = llm_agent._last_rationale

    # ── Nanopayment signal fetch (PayerAgent → ReceiverAgent) ───────────────
    # PayerAgent pays $0.000001 USDC per call to fetch a fresh paid signal.
    # ReceiverAgent validates the response before we act on it.
    try:
        if 'payer_agent' in dir():
            paid_response = payer_agent.get_signals(
                symbol=getattr(market_data, 'pair', 'BTC').replace('XXBTZUSD', 'BTC')[:3]
            )
            if receiver_agent.validate_receipt(paid_response):
                paid_data = paid_response.get('data', {})
                paid_direction = paid_data.get('direction', '')
                paid_confidence = float(paid_data.get('confidence', 0))
                # If paid signal agrees with consensus, small confidence boost
                if (paid_direction == 'bullish' and consensus_direction == VoteDirection.BUY) or                    (paid_direction == 'bearish' and consensus_direction == VoteDirection.SELL):
                    boost = round(paid_confidence * 0.05, 4)
                    consensus_confidence = min(0.95, consensus_confidence + boost)
                    logger.info(
                        f"[cyan]💳 Paid signal AGREES ({paid_direction}) "
                        f"+{boost:.4f} boost → confidence {consensus_confidence:.3f}[/cyan]"
                    )
                elif paid_direction in ('bullish', 'bearish'):
                    logger.info(
                        f"[yellow]💳 Paid signal DISAGREES ({paid_direction} vs "
                        f"{consensus_direction.value}) — no adjustment[/yellow]"
                    )
                logger.info(
                    f"[dim]💳 Nanopayment: receipts={receiver_agent.receipt_count()} "
                    f"total_spent={receiver_agent.total_spent_usdc():.6f} USDC[/dim]"
                )
    except Exception as _np_e:
        logger.debug(f"Nanopayment signal fetch skipped: {_np_e}")

    # ── BTC Correlation adjustment ────────────────────────────────────────────
    # If JSE/US stocks are lagging BTC → boost BUY confidence
    # If JSE/US stocks are beating BTC → suppress low-confidence BUY trades
    if btc_signal is not None:
        sig = getattr(btc_signal, 'signal', None)
        if sig == 'BUY_CRYPTO' and consensus_direction == VoteDirection.BUY:
            boost = min(0.10, abs(getattr(btc_signal, 'relative_strength', 0)) * 0.01)
            consensus_confidence = min(0.95, consensus_confidence + boost)
            logger.info(
                f"[green]BTC correlation BOOST +{boost:.3f} → "
                f"confidence now {consensus_confidence:.3f}[/green]"
            )
        elif sig == 'SELL_CRYPTO' and consensus_direction == VoteDirection.BUY:
            if consensus_confidence < 0.60:
                logger.info(
                    "[yellow]BTC correlation SUPPRESS — JSE outperforming BTC, "
                    "confidence too low — skipping trade[/yellow]"
                )
                return True  # skip this cycle

    # ── Alpaca US stock trade when correlation is strong ─────────────────────
    if (alpaca_client and alpaca_client.is_ready and
            btc_signal is not None and
            getattr(config, 'US_STOCKS_ENABLED', False)):
        sig = getattr(btc_signal, 'signal', None)
        rel = abs(getattr(btc_signal, 'relative_strength', 0))
        if sig == 'SELL_CRYPTO' and rel > 8.0 and not dry_run:
            # Rotate small amount into top US stock as hedge
            top_us = getattr(stock_market, 'US_TOP_STOCKS', ['SPY'])[:1]
            for ticker in top_us:
                try:
                    result = alpaca_client.place_order(
                        symbol=ticker,
                        notional=50.0,   # $50 paper trade
                        side='buy',
                        dry_run=dry_run,
                    )
                    logger.info(
                        f"[cyan]Alpaca paper BUY {ticker} $50 "
                        f"(hedge — JSE rel_strength={rel:.1f}%)[/cyan]"
                    )
                except Exception as _e:
                    logger.debug(f"Alpaca order failed: {_e}")

    # Sign votes for on-chain audit trail
    signed_votes_list = []
    try:
        signed_votes_list = reputation_client.sign_all_votes(
            [{"agent_id": v.agent_id, "direction": v.direction.value, "confidence": v.confidence} for v in votes],
            cycle=cycle_number
        )
    except Exception as e:
        logger.debug(f"[dim]Vote signing failed: {e}[/dim]")

    # Save cycle log for dashboard audit trail
    # Build stock signal dict for cycle log
    _stock_signal_log = {}
    if btc_signal is not None:
        _stock_signal_log = {
            "signal":             getattr(btc_signal, 'signal', ''),
            "btc_return_30d":     getattr(btc_signal, 'btc_return_30d', 0),
            "stock_return_30d":   getattr(btc_signal, 'stock_return_30d', 0),
            "relative_strength":  getattr(btc_signal, 'relative_strength', 0),
            "basket":             getattr(btc_signal, 'basket', ''),
        }

    save_cycle_log(
        cycle_number,
        consensus_direction,
        consensus_confidence,
        llm_rationale=llm_rationale,
        orderflow_metrics=None,
        signed_votes=signed_votes_list,
        strategy=active_strategy,
        stock_signal=_stock_signal_log,
    )

    # Load current positions for dashboard display
    current_positions = position_manager.get_open_positions() if hasattr(position_manager, 'get_open_positions') else []
    positions_data = []
    for pos in current_positions:
        positions_data.append({
            'trade_id': pos.trade_id if hasattr(pos, 'trade_id') else 'unknown',
            'direction': getattr(pos, 'direction', 'UNKNOWN'),
            'entry_price': float(getattr(pos, 'entry_price', 0)),
            'current_price': float(market_data.current_price),
            'unrealised_pnl_pct': float(pos.unrealised_pnl_pct(market_data.current_price)) if hasattr(pos, 'unrealised_pnl_pct') else 0,
            'size': float(getattr(pos, 'size_usd', 0)),
            'reason_opened': getattr(pos, 'reason_opened', 'Consensus signal')
        })

    # Save live decisions for dashboard
    # Load recent closed trades from weights for PnL display
    recent_closes = []
    try:
        import json as _j
        w = _j.load(open('nexus_weights.json'))
        for a in w:
            recent_closes.append({
                'agent_id': a.get('agent_id'),
                'pnl_total': a.get('pnl_total', 0),
                'wins': a.get('wins', 0),
                'trades_closed': a.get('trades_closed', 0),
            })
    except Exception:
        pass
    save_live_decisions(1, agent_decisions, consensus_direction, consensus_confidence, positions_data, recent_closes)

    # Check if vetoed or low confidence
    if consensus_direction == VoteDirection.HOLD:
        logger.info(f"[yellow]HOLD (confidence={consensus_confidence:.3f})[/yellow]")
        consensus_engine.record_hold(market_data, votes, market_data.current_price)
        return True

    if consensus_confidence < config.CONFIDENCE_THRESHOLD:
        logger.info(
            f"[yellow]Insufficient confidence {consensus_confidence:.3f} "
            f"< {config.CONFIDENCE_THRESHOLD}[/yellow]"
        )
        consensus_engine.record_hold(market_data, votes, market_data.current_price)
        return True

    # ============ STEP 4b: Check Trade Block ============
    # If direction is blocked due to repeated losses, reject trade
    if position_manager.is_direction_blocked(consensus_direction.value):
        block_status = position_manager.get_block_status()
        if consensus_direction == VoteDirection.BUY:
            remaining = block_status["buy_cycles_remaining"]
        else:
            remaining = block_status["sell_cycles_remaining"]
        
        logger.warning(
            f"[red]TRADE BLOCKED[/red]: {consensus_direction.value} blocked "
            f"for {remaining} more cycle(s) due to repeated losses"
        )
        consensus_engine.record_hold(market_data, votes, market_data.current_price)
        return True

    # ============ STEP 5: Size position ============
    atr_pct = 0.0
    if hasattr(market_data, "prism_risk") and market_data.prism_risk:
        atr_pct = market_data.prism_risk.atr_pct

    position_size_usd = compute_position_size(
        market_data.portfolio_value_usd,
        atr_pct,
        consensus_confidence,
    )

    # ============ STEP 6: Load equity curve for Sharpe calculation ============
    equity_curve = []
    try:
        with open(config.EQUITY_CURVE_FILE, "r") as f:
            equity_data = json.load(f)
            equity_curve = [e["equity"] for e in equity_data[-100:]]  # Last 100 points
    except FileNotFoundError:
        pass

    # ============ STEP 7: Run compliance checks ============
    trade_id = f"nexus_{timestamp}_{consensus_direction.value.lower()}"
    is_compliant, compliance_checks = compliance_engine.validate_trade_decision(
        market_data,
        position_size_usd,
        consensus_confidence,
        consensus_direction.value,
        equity_curve=equity_curve,
    )

    if not is_compliant:
        failed_checks = [c for c in compliance_checks if c.level.value == "FAIL"]
        logger.warning(
            f"[yellow]Trade blocked by compliance: {[c.rule_name for c in failed_checks]}[/yellow]"
        )
        return True

    # Log compliance details
    for check in compliance_checks:
        if check.level.value == "PASS":
            logger.debug(f"[green]✓ {check.rule_name}[/green]")

    # ============ STEP 8: Create trust marker ============
    trust_marker = validation_engine.create_trust_marker(
        trade_id,
        market_data,
        votes,
        consensus_direction.value,
        consensus_confidence,
    )

    volume = kraken_client.usd_to_volume(position_size_usd, market_data.current_price)

    logger.info(
        f"[bold green]{consensus_direction.value}[/bold green] "
        f"(conf={consensus_confidence:.3f}, size=${position_size_usd:.2f})"
    )

    # ============ STEP 9: Execute trade (or dry-run) ============
    if not dry_run:
        if consensus_direction == VoteDirection.BUY:
            kraken_client.market_buy(volume)
            position_manager.open_position(
                trade_id, "BUY", market_data.current_price,
                volume, entry_confidence=consensus_confidence,
            )
        elif consensus_direction == VoteDirection.SELL:
            kraken_client.market_sell(volume)
            position_manager.open_position(
                trade_id, "SELL", market_data.current_price,
                volume, entry_confidence=consensus_confidence,
            )

        # Sign and push on-chain
        signed_outcome = reputation_client.sign_trade_outcome(
            trade_id=trade_id,
            direction=consensus_direction.value,
            confidence=consensus_confidence,
            pnl_usd=0.0,
            agent_votes={v.agent_id: v.direction.value for v in votes},
        )
        if signed_outcome:
            reputation_client.push_outcome(signed_outcome, dry_run=False)
    else:
        logger.info(f"[dim]DRY-RUN: Would execute {consensus_direction.value} {volume} {config.PAIR}[/dim]")
        position_manager.open_position(
            trade_id, consensus_direction.value, market_data.current_price,
            volume, entry_confidence=consensus_confidence,
        )

        # Update positions for dashboard AFTER opening
        current_positions = position_manager.get_open_positions() if hasattr(position_manager, 'get_open_positions') else []
        positions_data = [{
            'trade_id': pos.trade_id if hasattr(pos, 'trade_id') else 'unknown',
            'direction': getattr(pos, 'direction', 'UNKNOWN'),
            'entry_price': float(getattr(pos, 'entry_price', 0)),
            'current_price': float(market_data.current_price),
            'unrealised_pnl_pct': float(pos.unrealised_pnl_pct(market_data.current_price)) if hasattr(pos, 'unrealised_pnl_pct') else 0,
            'size': float(getattr(pos, 'size_usd', 0)),
            'reason_opened': getattr(pos, 'reason_opened', 'Consensus signal')
        } for pos in current_positions]
        save_live_decisions(1, agent_decisions, consensus_direction, consensus_confidence, positions_data, recent_closes)

        signed_outcome = reputation_client.sign_trade_outcome(
            trade_id=trade_id,
            direction=consensus_direction.value,
            confidence=consensus_confidence,
            pnl_usd=0.0,
            agent_votes={v.agent_id: v.direction.value for v in votes},
        )
        if signed_outcome:
            reputation_client.push_outcome(signed_outcome, dry_run=True)

    # ============ STEP 10: Record equity curve ============
    position_manager.portfolio_equity_curve_add(
        market_data.cash_usd,
        market_data.current_price,
        timestamp,
    )

    return True


# ─── Market Data Builder ──────────────────────────────────────────────────────

class MarketDataBuilder:
    """Orchestrates data assembly from PRISM and Kraken."""

    def __init__(self, prism_client: PrismClient, kraken_client: KrakenClient):
        self.prism = prism_client
        self.kraken = kraken_client
        self.pair = config.PAIR
        self.symbol = config.PRISM_SYMBOL

    def build(self) -> Optional[MarketData]:
        """
        Assemble complete MarketData snapshot.
        Returns None if critical data (price, candles) unavailable.
        """
        try:
            # Fetch PRISM price (required)
            price_data = self.prism.get_price(self.symbol)
            if not price_data:
                logger.error("[red]Failed to fetch PRISM price — cannot proceed[/red]")
                return None

            current_price = float(price_data.get("price", 0))
            if current_price <= 0:
                logger.error("[red]Invalid price from PRISM[/red]")
                return None

            change_24h_pct = float(price_data.get("change_24h_pct", 0.0))
            volume_24h = float(price_data.get("volume_24h", 0.0))

            # Fetch PRISM candles (required)
            candles = self.prism.get_ohlcv(self.symbol, config.PRISM_OHLCV_INTERVAL)
            if not candles or len(candles) == 0:
                logger.error("[red]Failed to fetch PRISM candles — cannot proceed[/red]")
                return None

            # Fetch PRISM signals (optional, fallback to None)
            signal_1h = self.prism.get_signals(self.symbol, timeframe="1h")
            signal_4h = self.prism.get_signals(self.symbol, timeframe="4h")

            # Fetch PRISM risk (optional, fallback to None)
            prism_risk = self.prism.get_risk(self.symbol)

            # Fetch sentiment (optional) — news sentiment now handled by fetch_composite_sentiment()
            fear_greed = self._fetch_fear_greed()

            # Fetch social score from CoinGecko community data (optional)
            social_score = self._fetch_social_score()

            # Fetch news sentiment from CryptoPanic (optional)
            news_sentiment = self._fetch_news_sentiment()

            # Fetch portfolio from Kraken (required)
            portfolio_value, open_position = self.kraken.portfolio_summary()
            
            # Calculate available cash
            cash_usd = portfolio_value - open_position

            return MarketData(
                pair=self.pair,
                candles=candles,
                current_price=current_price,
                change_24h_pct=change_24h_pct,
                volume_24h=volume_24h,
                signal_1h=signal_1h,
                signal_4h=signal_4h,
                prism_risk=prism_risk,
                fear_greed_index=fear_greed,
                news_sentiment=news_sentiment,
                social_score=social_score,
                portfolio_value_usd=portfolio_value,
                open_position_usd=open_position,
                cash_usd=max(0.0, cash_usd),
            )

        except Exception as e:
            logger.error(f"[red]MarketDataBuilder.build() exception: {e}[/red]")
            return None

    def _fetch_fear_greed(self) -> Optional[int]:
        """
        Fetch Crypto Fear & Greed Index.
        """
        try:
            response = requests.get(config.FEAR_GREED_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and "data" in data and len(data["data"]) > 0:
                fng_value = int(data["data"][0].get("value", 50))
                return max(0, min(100, fng_value))
        except Exception as e:
            logger.debug(f"[dim]Fear & Greed fetch failed: {e}[/dim]")
        return None

    def _fetch_social_score(self) -> Optional[float]:
        """
        Fetch CoinGecko community data and extract social activity score.
        Normalizes Twitter followers (0-1 scale with 10M max).
        Returns 0.0-1.0 normalized value.
        """
        try:
            response = requests.get(config.COINGECKO_COMMUNITY, timeout=5)
            response.raise_for_status()
            data = response.json()

            # Extract community data
            community_data = data.get("community_data", {})
            twitter_followers = community_data.get("twitter_followers", 0)

            # Normalize to 0-1 scale (10M max is reasonable cap)
            max_followers = 10_000_000
            normalized_score = min(1.0, float(twitter_followers) / max_followers)
            return normalized_score

        except Exception as e:
            logger.debug(f"[dim]CoinGecko social score fetch failed: {e}[/dim]")
        return None

    def _fetch_news_sentiment(self) -> Optional[float]:
        """
        Fetch CryptoPanic news headlines and score sentiment.
        Uses simple keyword matching: +1 for bullish, -1 for bearish.
        Returns -1.0 to +1.0 sentiment average.
        """
        try:
            response = requests.get(config.CRYPTOPANIC_URL, timeout=5)
            response.raise_for_status()
            data = response.json()

            posts = data.get("results", [])
            if not posts:
                logger.debug("[dim]No CryptoPanic posts found[/dim]")
                return None

            # Bullish keywords
            bullish_words = {"bull", "surge", "rally", "gain", "peak", "record", "up", "strong", "bounce"}
            # Bearish keywords
            bearish_words = {"bear", "crash", "fall", "loss", "drop", "down", "weak", "sell"}

            sentiments = []
            for post in posts[:10]:  # Score last 10 posts
                title = (post.get("title") or "").lower()

                score = 0.0
                bullish_count = sum(1 for word in bullish_words if word in title)
                bearish_count = sum(1 for word in bearish_words if word in title)

                if bullish_count > bearish_count:
                    score = min(1.0, bullish_count / 2.0)
                elif bearish_count > bullish_count:
                    score = -min(1.0, bearish_count / 2.0)

                sentiments.append(score)

            if sentiments:
                avg_sentiment = sum(sentiments) / len(sentiments)
                return max(-1.0, min(1.0, avg_sentiment))

            return None

        except Exception as e:
            logger.debug(f"[dim]CryptoPanic news sentiment fetch failed: {e}[/dim]")
        return None

    # News sentiment is now handled by fetch_composite_sentiment() in agents/sentiment.py


def live_trading_loop(dry_run: bool = False):
    """Main trading loop."""
    logger.info("[bold green]Starting NEXUS live trading engine[/bold green]")

    # Initialize clients
    kraken_client = KrakenClient(dry_run=dry_run)
    prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)
    reputation_client = ReputationClient()

    # ── Stock + Alpaca clients (non-blocking — failures don't stop crypto loop)
    stock_market = None
    alpaca_client = None
    try:
        stock_market = StockMarketClient()
        logger.info("[green]✅ StockMarketClient ready (Yahoo Finance — JSE + US)[/green]")
    except Exception as _e:
        logger.warning(f"[yellow]⚠️  StockMarketClient unavailable: {_e}[/yellow]")
    try:
        alpaca_client = AlpacaClient()
        if alpaca_client.is_ready:
            mode = "LIVE" if alpaca_client.is_live else "PAPER"
            logger.info(f"[green]✅ AlpacaClient ready ({mode} trading)[/green]")
        else:
            logger.info("[yellow]⚠️  AlpacaClient: add ALPACA_API_KEY + ALPACA_API_SECRET to .env[/yellow]")
    except Exception as _e:
        logger.warning(f"[yellow]⚠️  AlpacaClient unavailable: {_e}[/yellow]")

    # Initialize agents
    agents = create_default_agents(anthropic_api_key=config.ANTHROPIC_API_KEY)

    # Initialize engines
    consensus_engine = ConsensusEngine()
    compliance_engine = ComplianceEngine()
    validation_engine = ValidationEngine()
    yield_optimizer = YieldOptimizer()
    regime_detector = RegimeDetector()
    position_manager = PositionManager()
    leaderboard_manager = LeaderboardManager()  # For lablab.ai competition

    # Register agents
    for agent in agents:
        consensus_engine.register_agent(agent.agent_id)

    logger.info(f"[green]Initialized {len(agents)} agents (including mean_reversion)[/green]")
    logger.info(f"[bold blue]Position Manager[/bold blue]: Stop-loss/take-profit exits with feedback loop")
    logger.info(f"[bold blue]Regime Detector[/bold blue]: Market regime classification with dynamic re-weighting")
    logger.info(f"[bold blue]Compliance Engine[/bold blue]: Best Compliance & Risk Guardrails")
    logger.info(f"[bold blue]Validation Engine[/bold blue]: Best Trustless Trading Agent & Validation Model")
    logger.info(f"[bold blue]Yield Optimizer[/bold blue]: Best Yield & Risk-Adjusted Returns")
    logger.info(f"[bold green]Leaderboard Manager[/bold green]: lablab.ai competition tracking via Kraken API")
    logger.info(f"[dim]Loop interval: {config.LOOP_INTERVAL_SECONDS}s[/dim]")

    # Trading loop
    cycle_count = 0
    last_submission_cycle = 0
    submission_interval = 120  # Submit every 120 cycles (~10 hours at 5min intervals)
    
    try:
        while True:
            cycle_count += 1
            logger.info(f"\n[bold]Cycle #{cycle_count}[/bold]")
            # Build market data
            builder = MarketDataBuilder(prism_client, kraken_client)
            market_data = builder.build()

            if not market_data:
                logger.error("[red]Could not build market data — retrying in 30s[/red]")
                time.sleep(30)
                continue

            # Execute trade cycle with all engines
            # BTC correlation signal — runs before trade_cycle
            btc_signal = None
            if stock_market and getattr(config, 'BTC_CORRELATION_ENABLED', False):
                try:
                    use_jse = getattr(config, 'JSE_ENABLED', True)
                    top_n   = getattr(config, 'JSE_TOP_N', 20)
                    btc_signal = stock_market.btc_correlation_signal(
                        use_jse=use_jse, top_n=top_n
                    )
                    logger.info(
                        f"[bold blue]BTC Correlation[/bold blue]: "
                        f"{btc_signal.signal} | "
                        f"BTC 30d={btc_signal.btc_return_30d:+.1f}% "
                        f"Stock 30d={btc_signal.stock_return_30d:+.1f}%"
                    )
                except Exception as _e:
                    logger.debug(f"BTC correlation signal failed: {_e}")

            trade_cycle(
                market_data,
                agents,
                consensus_engine,
                kraken_client,
                reputation_client,
                compliance_engine,
                validation_engine,
                yield_optimizer,
                position_manager,
                regime_detector,
                cycle_number=cycle_count,
                dry_run=dry_run,
                btc_signal=btc_signal,
                alpaca_client=alpaca_client,
                stock_market=stock_market,
            )

            # Periodic leaderboard submission (every 120 cycles)
            if cycle_count - last_submission_cycle >= submission_interval:
                logger.info(f"[bold green]📊 Periodic leaderboard submission (cycle {cycle_count})[/bold green]")
                leaderboard_manager.submit_to_leaderboard()
                last_submission_cycle = cycle_count

            logger.info(f"[dim]Sleeping {config.LOOP_INTERVAL_SECONDS}s...[/dim]")
            time.sleep(config.LOOP_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("\n[yellow]Shutdown requested[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[red]Unhandled exception in trading loop: {e}[/red]")
        sys.exit(1)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="NEXUS — Self-Improving Multi-Agent Trading System")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without real orders")
    parser.add_argument("--live", action="store_true", help="Execute real trades (requires sandbox capital claimed)")
    parser.add_argument("--leaderboard", action="store_true", help="Print agent leaderboard and exit")
    parser.add_argument("--lablab-status", action="store_true", help="Print lablab.ai competition status and exit")
    parser.add_argument("--submit-lablab", action="store_true", help="Submit current performance to lablab.ai leaderboard")
    parser.add_argument("--mint-agent-erc721", action="store_true", help="Mint ERC-721 Agent Identity and register on-chain")
    parser.add_argument("--claim-sandbox-capital", type=float, default=0.0, help="Claim sandbox capital (amount in USD, e.g., 10000.0)")
    parser.add_argument("--capital-status", action="store_true", help="Check sandbox capital sub-account status and exit")
    parser.add_argument("--ping", action="store_true", help="Verify PRISM and Kraken connectivity")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")
    parser.add_argument("--check-prism", action="store_true", help="Check PRISM API key and connectivity only")

    args = parser.parse_args()
    setup_logging(args.verbose)

    # --ping: connectivity check
    if args.ping:
        kraken_client = KrakenClient()
        prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)
        success = ping_prism_and_kraken(prism_client, kraken_client)
        sys.exit(0 if success else 1)

    # --check-prism: test PRISM API only (no Kraken needed)
    if args.check_prism:
        kraken_client = KrakenClient()
        prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)
        console.print("[bold]NEXUS --check-prism: PRISM API Check[/bold]")
        resolved = prism_client.resolve_asset(config.PRISM_SYMBOL)
        if resolved and resolved.get("symbol") == config.PRISM_SYMBOL:
            console.print(f"[green]✓ PRISM API key is valid. Symbol: {resolved['symbol']}[/green]")
            sys.exit(0)
        else:
            console.print("[red]✗ PRISM API key invalid or unreachable[/red]")
            sys.exit(1)

    # --leaderboard: print agent leaderboard and exit
    if args.leaderboard:
        consensus_engine = ConsensusEngine()
        print(consensus_engine.leaderboard())
        sys.exit(0)

    # --lablab-status: print lablab.ai leaderboard status and exit
    if args.lablab_status:
        leaderboard_manager = LeaderboardManager()
        print(leaderboard_manager.leaderboard_status())
        sys.exit(0)

    # --submit-lablab: submit to leaderboard and exit
    if args.submit_lablab:
        leaderboard_manager = LeaderboardManager()
        success = leaderboard_manager.submit_to_leaderboard()
        sys.exit(0 if success else 1)

    # --mint-agent-erc721: mint agent identity and register on-chain
    if args.mint_agent_erc721:
        logger.info("[bold cyan]Minting ERC-721 Agent Identities[/bold cyan]")
        reputation_client = ReputationClient()
        agents = create_default_agents(anthropic_api_key=config.ANTHROPIC_API_KEY)
        
        for agent in agents:
            logger.info(f"[cyan]Processing agent: {agent.agent_id}[/cyan]")
            identity = reputation_client.mint_agent_erc721_identity(agent.agent_id)
            if identity:
                logger.info(
                    f"[green]✓ {agent.agent_id}: ERC-721 identity prepared[/green]\n"
                    f"  Signature: {identity['signature'][:20]}...\n"
                    f"  Status: {identity['status']}"
                )
                reputation_client.register_agent_on_chain(agent.agent_id, token_id=None)
            else:
                logger.error(f"[red]✗ {agent.agent_id}: Failed to mint ERC-721[/red]")
        
        logger.info("[bold green]✓ All agents registered for ERC-721 minting[/bold green]")
        sys.exit(0)

    # --claim-sandbox-capital: claim sandbox sub-account from vault
    if args.claim_sandbox_capital > 0:
        logger.info("[bold cyan]Claiming Hackathon Sandbox Capital[/bold cyan]")
        capital_manager = SandboxCapitalManager(
            agent_id="nexus_ensemble",
            team_name="NEXUS Trading AI",
        )
        
        allocation = capital_manager.claim_sandbox_sub_account(
            capital_type="TESTNET",
            initial_capital_usd=args.claim_sandbox_capital,
        )
        
        if allocation:
            logger.info(f"[bold green]✓ Sandbox capital claimed![/bold green]")
            logger.info(f"[green]Sub-account: {allocation['sub_account_address']}[/green]")
            logger.info(f"[green]Capital allocated: ${allocation['capital_allocated_usd']:,.2f}[/green]")
            logger.info(f"[green]Type: {allocation['capital_type']}[/green]")
        else:
            logger.error("[red]Failed to claim sandbox capital[/red]")
        
        sys.exit(0)

    # --capital-status: check sandbox capital status
    if args.capital_status:
        logger.info("[bold cyan]Checking Sandbox Capital Status[/bold cyan]")
        capital_manager = SandboxCapitalManager(agent_id="nexus_ensemble")
        status = capital_manager.get_sub_account_status()
        
        logger.info(f"Agent ID: {status['agent_id']}")
        logger.info(f"Team: {status['team_name']}")
        logger.info(f"Sub-account created: {status['sub_account_created']}")
        if status['sub_account_created']:
            logger.info(f"Sub-account address: {status['sub_account_address']}")
            logger.info(f"Capital allocated: ${status['capital_allocated_usd']:,.2f}")
            logger.info(f"Capital type: {status['capital_type']}")
        
        sys.exit(0)

    # Determine execution mode
    dry_run = args.dry_run or not args.live
    
    if dry_run:
        logger.info("[bold yellow]Running in DRY-RUN mode (no real orders)[/bold yellow]")
    else:
        logger.info("[bold red]Running in LIVE mode (real orders enabled)[/bold red]")
    
    # Start trading loop
    live_trading_loop(dry_run=dry_run)


if __name__ == "__main__":
    main()
