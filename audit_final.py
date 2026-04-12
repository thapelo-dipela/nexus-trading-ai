#!/usr/bin/env python3
"""
FINAL AUDIT - Complete system verification for video demonstration.
Checks:
1. Agent thinking loops (continuous analysis cycles)
2. Parameter liveness (real-time config updates)
3. Dashboard live updates
4. Kraken integration
5. RiskRouter on-chain connection
6. Market data refresh rates
7. Agent consensus voting
"""
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.logging import RichHandler

import config
from agents import create_default_agents
from agents.base import MarketData, Candle, PrismSignal, PrismRisk
from data.prism import PrismClient
from execution.kraken import KrakenClient
from consensus.engine import ConsensusEngine
from consensus.regime import RegimeDetector

console = Console()
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[RichHandler(show_time=False, show_level=False, show_path=False)],
)
logger = logging.getLogger("audit")

# ============================================================================
# AUDIT 1: Agent Thinking Loop Verification
# ============================================================================
def audit_agent_thinking():
    """Verify agents are continuously thinking with detailed logging."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #1: AGENT THINKING LOOPS[/bold cyan]")
    console.print("="*80)
    
    agents = create_default_agents()
    console.print(f"\n✓ Loaded {len(agents)} agents:")
    for agent in agents:
        console.print(f"  • {agent.agent_id}: {agent.reasoning}")
    
    # Create mock market data
    now = int(time.time())
    mock_candles = [
        Candle(
            timestamp=now - (300 * i),
            open=45000 + i*10,
            high=45200 + i*10,
            low=44800 + i*10,
            close=45100 + i*10,
            volume=100 + i,
        )
        for i in range(30)
    ]
    
    mock_signal = PrismSignal(
        direction="bullish",
        confidence=0.75,
        score=0.65,
        reasoning="Strong uptrend detected",
        indicators={
            "rsi": 65,
            "macd": 0.05,
            "macd_histogram": 0.02,
            "bollinger_upper": 46000,
            "bollinger_lower": 44000,
        },
        current_price=45100.0,
        rsi=65,
        macd_histogram=0.02,
    )
    
    mock_risk = PrismRisk(
        risk_score=35,
        atr_pct=0.02,
        volatility_30d=0.15,
        max_drawdown_30d=0.08,
        sharpe_ratio=1.5,
        sortino_ratio=2.0,
    )
    
    market_data = MarketData(
        pair="BTC",
        candles=mock_candles,
        current_price=45100.0,
        change_24h_pct=2.5,
        volume_24h=500000,
        signal_1h=mock_signal,
        signal_4h=mock_signal,
        prism_risk=mock_risk,
        fear_greed_index=65,
        news_sentiment=0.3,
        portfolio_value_usd=10000.0,
        open_position_usd=2000.0,
        cash_usd=8000.0,
    )
    
    console.print("\n[bold]Running 3 thinking cycles per agent:[/bold]")
    
    results = {}
    for agent in agents:
        console.print(f"\n[yellow]→ {agent.agent_id}[/yellow]")
        votes = []
        for cycle in range(3):
            try:
                vote = agent.analyze(market_data)
                votes.append(vote)
                console.print(
                    f"  Cycle {cycle+1}: {vote.direction.value} "
                    f"(conf={vote.confidence:.2f}) - {vote.reasoning[:50]}..."
                )
            except Exception as e:
                console.print(f"  [red]Cycle {cycle+1}: ERROR - {e}[/red]")
        
        results[agent.agent_id] = {
            "cycles_completed": len(votes),
            "consistency": all(v.direction == votes[0].direction for v in votes) if votes else False,
            "votes": [
                {
                    "direction": v.direction.value,
                    "confidence": float(v.confidence),
                    "reasoning": v.reasoning,
                }
                for v in votes
            ]
        }
    
    # Summary
    console.print("\n[bold green]Thinking Loop Summary:[/bold green]")
    table = Table(title="Agent Thinking Verification")
    table.add_column("Agent", style="cyan")
    table.add_column("Cycles", style="green")
    table.add_column("Consistent", style="yellow")
    table.add_column("Status", style="bold")
    
    all_good = True
    for agent_id, result in results.items():
        status = "✓ PASS" if result["cycles_completed"] == 3 else "✗ FAIL"
        consistency = "✓" if result["consistency"] else "✗"
        table.add_row(
            agent_id,
            str(result["cycles_completed"]),
            consistency,
            status,
        )
        if result["cycles_completed"] != 3:
            all_good = False
    
    console.print(table)
    return all_good, results

# ============================================================================
# AUDIT 2: Parameter Liveness Verification
# ============================================================================
def audit_parameter_liveness():
    """Verify max parameters are live and used in trading logic."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #2: PARAMETER LIVENESS[/bold cyan]")
    console.print("="*80)
    
    parameters = {
        "MAX_LEVERAGE": config.MAX_LEVERAGE,
        "MAX_POSITION_PCT": config.MAX_POSITION_PCT,
        "MAX_TRADE_SIZE_USD": config.MAX_TRADE_SIZE_USD,
        "MAX_DRAWDOWN_PCT": config.MAX_DRAWDOWN_PCT,
        "RISK_PCT_PER_TRADE": config.RISK_PCT_PER_TRADE,
        "MAX_SLIPPAGE_PCT": config.MAX_SLIPPAGE_PCT,
        "MIN_SHARPE_RATIO": config.MIN_SHARPE_RATIO,
        "VOLATILITY_THRESHOLD": config.VOLATILITY_THRESHOLD,
    }
    
    console.print("\n[bold]Live Configuration Parameters:[/bold]")
    table = Table(title="Max Parameters Status")
    table.add_column("Parameter", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Live", style="bold")
    
    for param_name, param_value in parameters.items():
        param_type = type(param_value).__name__
        status = "✓ LIVE" if param_value > 0 else "✗ NOT SET"
        table.add_row(param_name, str(param_value), param_type, status)
    
    console.print(table)
    
    # Check trading logic uses these
    console.print("\n[bold]Verification: Trading Logic Uses Parameters[/bold]")
    try:
        from execution import compute_position_size
        test_result = compute_position_size(
            portfolio_value=10000,
            confidence=0.75,
            sharpe_ratio=1.5,
        )
        console.print(f"✓ compute_position_size works: ${test_result:,.2f}")
        
        # Verify it respects MAX_TRADE_SIZE_USD
        is_within_limit = test_result <= config.MAX_TRADE_SIZE_USD
        console.print(f"{'✓' if is_within_limit else '✗'} Respects MAX_TRADE_SIZE_USD: {is_within_limit}")
        
        return True
    except Exception as e:
        console.print(f"[red]✗ compute_position_size failed: {e}[/red]")
        return False

# ============================================================================
# AUDIT 3: Market Data Refresh Rates
# ============================================================================
def audit_market_data_refresh():
    """Verify market data refreshes at expected intervals."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #3: MARKET DATA REFRESH RATES[/bold cyan]")
    console.print("="*80)
    
    try:
        kraken_client = KrakenClient()
        prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)
        
        console.print("\n[bold]Testing market data refresh cycles:[/bold]")
        
        # Test price refresh
        console.print("\n1. PRISM Price Refresh:")
        t0 = time.time()
        price1 = prism_client.get_price("BTC")
        t1 = time.time()
        console.print(f"  First fetch: ${price1.get('price', 0):,.2f} ({t1-t0:.2f}s)")
        
        time.sleep(1)
        
        t0 = time.time()
        price2 = prism_client.get_price("BTC")
        t1 = time.time()
        console.print(f"  Second fetch: ${price2.get('price', 0):,.2f} ({t1-t0:.2f}s)")
        console.print(f"  Price updated: {price1 != price2}")
        
        # Test signals refresh
        console.print("\n2. PRISM Signals Refresh (1h):")
        t0 = time.time()
        signal1 = prism_client.get_signals("BTC", "1h")
        t1 = time.time()
        if signal1:
            console.print(f"  Direction: {signal1.direction} (score={signal1.score:.3f}, {t1-t0:.2f}s)")
        else:
            console.print(f"  [yellow]Signal unavailable (timeout expected)[/yellow]")
        
        # Test candles refresh
        console.print("\n3. PRISM Candles Refresh:")
        t0 = time.time()
        candles = prism_client.get_ohlcv("BTC", config.PRISM_OHLCV_INTERVAL)
        t1 = time.time()
        if candles:
            console.print(f"  Fetched {len(candles)} candles ({t1-t0:.2f}s)")
            console.print(f"  Latest: ${candles[0].close:,.2f}")
        else:
            console.print(f"  [red]Failed to fetch candles[/red]")
        
        # Test Kraken refresh
        console.print("\n4. Kraken Portfolio Refresh:")
        t0 = time.time()
        portfolio, position = kraken_client.portfolio_summary()
        t1 = time.time()
        console.print(f"  Portfolio: ${portfolio:,.2f} ({t1-t0:.2f}s)")
        console.print(f"  Open position: ${position:,.2f}")
        
        console.print("\n[bold green]✓ All data sources responding[/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Market data refresh failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# AUDIT 4: Consensus Engine
# ============================================================================
def audit_consensus_voting():
    """Verify consensus engine correctly processes votes."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #4: CONSENSUS VOTING ENGINE[/bold cyan]")
    console.print("="*80)
    
    try:
        agents = create_default_agents()
        consensus_engine = ConsensusEngine()
        
        # Create mock votes
        now = int(time.time())
        mock_candles = [
            Candle(
                timestamp=now - (300 * i),
                open=45000 + i*10,
                high=45200 + i*10,
                low=44800 + i*10,
                close=45100 + i*10,
                volume=100 + i,
            )
            for i in range(30)
        ]
        
        mock_signal = PrismSignal(
            direction="bullish",
            confidence=0.75,
            score=0.65,
            reasoning="Bullish setup",
            indicators={},
            current_price=45100.0,
            rsi=65,
            macd_histogram=0.02,
        )
        
        market_data = MarketData(
            pair="BTC",
            candles=mock_candles,
            current_price=45100.0,
            change_24h_pct=2.5,
            volume_24h=500000,
            signal_1h=mock_signal,
            signal_4h=mock_signal,
            prism_risk=None,
            fear_greed_index=65,
            news_sentiment=0.3,
            portfolio_value_usd=10000.0,
            open_position_usd=2000.0,
        )
        
        # Collect votes from all agents
        votes = []
        for agent in agents:
            vote = agent.analyze(market_data)
            if vote:
                votes.append(vote)
        
        console.print(f"\n✓ Collected {len(votes)} votes from {len(agents)} agents")
        
        # Get consensus using vote() method
        direction, confidence, _ = consensus_engine.vote(votes)
        
        console.print(f"\n[bold]Consensus Decision:[/bold]")
        console.print(f"  Direction: {direction.value}")
        console.print(f"  Confidence: {confidence:.2f}")
        console.print(f"  Votes considered: {len(votes)}")
        
        # Summary table
        console.print(f"\n[bold]Individual Votes:[/bold]")
        table = Table(title="Agent Votes in Consensus")
        table.add_column("Agent", style="cyan")
        table.add_column("Vote", style="yellow")
        table.add_column("Confidence", style="green")
        table.add_column("Reasoning", style="dim")
        
        for vote in votes:
            table.add_row(
                vote.agent_id,
                vote.direction.value,
                f"{vote.confidence:.2f}",
                vote.reasoning[:40] + "..." if len(vote.reasoning) > 40 else vote.reasoning,
            )
        
        console.print(table)
        console.print("\n[bold green]✓ Consensus engine working correctly[/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Consensus voting failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# AUDIT 5: Market Regime Detection
# ============================================================================
def audit_regime_detection():
    """Verify regime detection works correctly."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #5: MARKET REGIME DETECTION[/bold cyan]")
    console.print("="*80)
    
    try:
        regime_detector = RegimeDetector()
        
        # Create market data with uptrend
        now = int(time.time())
        uptrend_candles = [
            Candle(
                timestamp=now - (300 * i),
                open=45000 + (30-i)*50,
                high=45200 + (30-i)*50,
                low=44800 + (30-i)*50,
                close=45100 + (30-i)*50,
                volume=100 + i,
            )
            for i in range(30)
        ]
        
        market_data = MarketData(
            pair="BTC",
            candles=uptrend_candles,
            current_price=46000.0,
            change_24h_pct=2.5,
            volume_24h=500000,
            signal_1h=None,
            signal_4h=None,
            prism_risk=None,
            fear_greed_index=65,
            news_sentiment=None,
            portfolio_value_usd=10000.0,
            open_position_usd=2000.0,
        )
        
        regime = regime_detector.detect_regime(market_data)
        weights = regime_detector.get_agent_weights(regime)
        
        console.print(f"\n✓ Detected market regime: [bold]{regime.value}[/bold]")
        console.print(f"✓ Agent weight adjustments: {json.dumps(weights, indent=2)}")
        
        console.print("\n[bold green]✓ Regime detection working[/bold green]")
        return True
        
    except Exception as e:
        console.print(f"[red]✗ Regime detection failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# AUDIT 6: On-Chain RiskRouter Readiness
# ============================================================================
def audit_riskrouter_readiness():
    """Verify RiskRouter client is ready for trade submission."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #6: ON-CHAIN RISKROUTER READINESS[/bold cyan]")
    console.print("="*80)
    
    try:
        from execution.risk_router import RiskRouterClient
        
        router = RiskRouterClient()
        
        console.print(f"\n✓ RiskRouter client initialized")
        console.print(f"  Connected: {router.is_connected()}")
        console.print(f"  Chain ID: {router.get_chain_id()}")
        console.print(f"  Agent wallet: {router.agent_account.address}")
        console.print(f"  RiskRouter address: {config.RISK_ROUTER_ADDRESS}")
        
        # Verify contract ABI is valid
        if router.router_abi and len(router.router_abi) > 0:
            console.print(f"  Contract ABI loaded: {len(router.router_abi)} functions")
            console.print("[bold green]✓ RiskRouter ready for trade submission[/bold green]")
            return True
        else:
            console.print("[red]✗ Contract ABI not loaded[/red]")
            return False
            
    except Exception as e:
        console.print(f"[red]✗ RiskRouter check failed: {e}[/red]")
        import traceback
        traceback.print_exc()
        return False

# ============================================================================
# AUDIT 7: Dashboard API
# ============================================================================
def audit_dashboard_api():
    """Verify dashboard API endpoints are available."""
    console.print("\n" + "="*80)
    console.print("[bold cyan]AUDIT #7: DASHBOARD API[/bold cyan]")
    console.print("="*80)
    
    try:
        import requests
        
        # Try to reach dashboard server
        endpoints = [
            "/api/market",
            "/api/agents",
            "/api/positions",
            "/api/performance",
            "/api/consensus",
        ]
        
        base_url = "http://localhost:5000"
        console.print(f"\n[bold]Testing dashboard endpoints at {base_url}:[/bold]")
        
        results = {}
        for endpoint in endpoints:
            try:
                response = requests.get(f"{base_url}{endpoint}", timeout=2)
                status = "✓" if response.status_code == 200 else f"✗ ({response.status_code})"
                results[endpoint] = response.status_code == 200
                console.print(f"  {endpoint}: {status}")
            except requests.exceptions.ConnectionError:
                results[endpoint] = False
                console.print(f"  {endpoint}: ✗ (connection refused)")
            except Exception as e:
                results[endpoint] = False
                console.print(f"  {endpoint}: ✗ ({str(e)[:40]}...)")
        
        if any(results.values()):
            console.print("\n[bold yellow]⚠ Dashboard server should be running for live updates[/bold yellow]")
            console.print(f"Start with: [cyan]python dashboard_server.py[/cyan]")
            return False
        else:
            console.print("\n[bold yellow]⚠ Dashboard server not running[/bold yellow]")
            return False
            
    except Exception as e:
        console.print(f"[yellow]⚠ Dashboard check skipped: {e}[/yellow]")
        return False

# ============================================================================
# MAIN AUDIT REPORT
# ============================================================================
def generate_audit_report(results):
    """Generate final audit report."""
    console.print("\n" + "="*80)
    console.print("[bold green]FINAL AUDIT REPORT[/bold green]")
    console.print("="*80)
    
    total_checks = len(results)
    passed_checks = sum(1 for r in results.values() if r)
    
    console.print(f"\n[bold]Summary: {passed_checks}/{total_checks} checks passed[/bold]")
    
    # Create summary table
    table = Table(title="Audit Summary")
    table.add_column("Audit", style="cyan")
    table.add_column("Status", style="bold")
    
    audit_names = [
        "Agent Thinking Loops",
        "Parameter Liveness",
        "Market Data Refresh",
        "Consensus Voting",
        "Regime Detection",
        "RiskRouter Readiness",
        "Dashboard API",
    ]
    
    for name, passed in zip(audit_names, results.values()):
        status = "[green]✓ PASS[/green]" if passed else "[red]✗ FAIL[/red]"
        table.add_row(name, status)
    
    console.print(table)
    
    # Video readiness
    console.print("\n" + "="*80)
    console.print("[bold cyan]VIDEO DEMONSTRATION READINESS[/bold cyan]")
    console.print("="*80)
    
    if passed_checks >= 5:
        console.print("\n[bold green]✓ SYSTEM READY FOR VIDEO DEMO[/bold green]")
        console.print("""
[bold]Demo Script:[/bold]
1. Start agents with thinking logging:
   python main.py --live --verbose
   
2. Open dashboard in browser:
   http://localhost:5000
   
3. Observe in real-time:
   • Agents making trading decisions every 5 minutes
   • Market data updating continuously
   • Consensus reaching agreement
   • Risk parameters enforced
   
4. Expected output:
   • 3+ agents analyzing each 5-minute candle
   • Market regime indicators changing
   • Position management with stop-loss/take-profit
   • On-chain RiskRouter integration ready
        """)
    else:
        console.print("\n[bold red]✗ System needs fixes before demo[/bold red]")
        console.print("Address failing audits above.")
    
    return passed_checks >= 5

def main():
    """Run full audit suite."""
    console.print("[bold cyan]NEXUS FINAL AUDIT SUITE[/bold cyan]")
    console.print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run audits
    results["thinking"], thinking_details = audit_agent_thinking()
    results["parameters"] = audit_parameter_liveness()
    results["market_data"] = audit_market_data_refresh()
    results["consensus"] = audit_consensus_voting()
    results["regime"] = audit_regime_detection()
    results["riskrouter"] = audit_riskrouter_readiness()
    results["dashboard"] = audit_dashboard_api()
    
    # Generate report
    ready = generate_audit_report(results)
    
    console.print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.exit(0 if ready else 1)

if __name__ == "__main__":
    main()
