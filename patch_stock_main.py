"""
patch_stock_main.py
Integrates StockMarketClient + AlpacaClient into main.py.

What this does:
  1. Adds imports for StockMarketClient and AlpacaClient
  2. Initialises both clients in live_trading_loop
  3. Fetches BTC correlation signal each cycle and logs it
  4. When BTC correlation fires BUY_CRYPTO, boosts consensus confidence
  5. When BTC correlation fires SELL_CRYPTO, suppresses low-confidence trades
  6. Executes Alpaca paper trades for US stocks when signal is strong
  7. Logs stock signal to nexus_cycle_log.json for dashboard display
"""
import re
import shutil
from pathlib import Path

TARGET = Path("main.py")
BACKUP = Path("main.py.stock.bak")

if not TARGET.exists():
    print(f"ERROR: {TARGET} not found. Run from project root.")
    exit(1)

shutil.copy(TARGET, BACKUP)
print(f"📦 Backup → {BACKUP}")

src = TARGET.read_text()
patches = []

# ── PATCH 1: Add imports after existing imports ───────────────────────────────
OLD_IMPORT = "from data.prism import PrismClient"
NEW_IMPORT = """from data.prism import PrismClient
from data.stock_market import StockMarketClient
from execution.alpaca_client import AlpacaClient"""

if "StockMarketClient" not in src:
    if OLD_IMPORT in src:
        src = src.replace(OLD_IMPORT, NEW_IMPORT, 1)
        patches.append("✅ PATCH 1 — imports: StockMarketClient + AlpacaClient")
    else:
        patches.append("⚠️  SKIP 1 — import anchor not found")
else:
    patches.append("⚠️  SKIP 1 — imports already present")

# ── PATCH 2: Initialise clients in live_trading_loop ─────────────────────────
OLD_LOOP_INIT = "    # Initialize clients\n    kraken_client = KrakenClient(dry_run=dry_run)"
NEW_LOOP_INIT = """    # Initialize clients
    kraken_client = KrakenClient(dry_run=dry_run)"""

OLD_AFTER_PRISM = "    prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)\n    reputation_client = ReputationClient()"
NEW_AFTER_PRISM = """    prism_client = PrismClient(config.PRISM_API_KEY, kraken_client)
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
        logger.warning(f"[yellow]⚠️  AlpacaClient unavailable: {_e}[/yellow]")"""

if "StockMarketClient()" not in src:
    if OLD_AFTER_PRISM in src:
        src = src.replace(OLD_AFTER_PRISM, NEW_AFTER_PRISM, 1)
        patches.append("✅ PATCH 2 — initialise StockMarketClient + AlpacaClient in loop")
    else:
        patches.append("⚠️  SKIP 2 — init anchor not found")
else:
    patches.append("⚠️  SKIP 2 — clients already initialised")

# ── PATCH 3: Pass clients into trade_cycle call ───────────────────────────────
OLD_TRADE_CALL = """            trade_cycle(
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
            )"""

NEW_TRADE_CALL = """            # BTC correlation signal — runs before trade_cycle
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
            )"""

if "btc_signal" not in src:
    if OLD_TRADE_CALL in src:
        src = src.replace(OLD_TRADE_CALL, NEW_TRADE_CALL, 1)
        patches.append("✅ PATCH 3 — BTC correlation + client args in trade_cycle call")
    else:
        patches.append("⚠️  SKIP 3 — trade_cycle call anchor not found")
else:
    patches.append("⚠️  SKIP 3 — btc_signal already present")

# ── PATCH 4: Add btc_signal + alpaca_client params to trade_cycle signature ───
OLD_SIGNATURE = """def trade_cycle(
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
) -> bool:"""

NEW_SIGNATURE = """def trade_cycle(
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
) -> bool:"""

if "btc_signal=None" not in src:
    if OLD_SIGNATURE in src:
        src = src.replace(OLD_SIGNATURE, NEW_SIGNATURE, 1)
        patches.append("✅ PATCH 4 — trade_cycle signature extended")
    else:
        patches.append("⚠️  SKIP 4 — signature anchor not found")
else:
    patches.append("⚠️  SKIP 4 — signature already extended")

# ── PATCH 5: Use BTC correlation to adjust consensus inside trade_cycle ────────
OLD_CONSENSUS = """    # Extract LLM rationale (prefer from engine, fallback to direct agent)
    llm_rationale = llm_rationale_from_engine or ""
    if not llm_rationale and llm_agent and hasattr(llm_agent, '_last_rationale'):
        llm_rationale = llm_agent._last_rationale"""

NEW_CONSENSUS = """    # Extract LLM rationale (prefer from engine, fallback to direct agent)
    llm_rationale = llm_rationale_from_engine or ""
    if not llm_rationale and llm_agent and hasattr(llm_agent, '_last_rationale'):
        llm_rationale = llm_agent._last_rationale

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
                    logger.debug(f"Alpaca order failed: {_e}")"""

if "BTC Correlation adjustment" not in src:
    if OLD_CONSENSUS in src:
        src = src.replace(OLD_CONSENSUS, NEW_CONSENSUS, 1)
        patches.append("✅ PATCH 5 — BTC correlation adjusts consensus + Alpaca hedge")
    else:
        patches.append("⚠️  SKIP 5 — consensus anchor not found")
else:
    patches.append("⚠️  SKIP 5 — BTC correlation logic already present")

# ── PATCH 6: Log stock signal into save_cycle_log call ───────────────────────
OLD_SAVE_CYCLE = """    save_cycle_log(
        cycle_number,
        consensus_direction,
        consensus_confidence,
        llm_rationale=llm_rationale,
        orderflow_metrics=None,  # Can be enriched later from agent data
        signed_votes=signed_votes_list,
        strategy=active_strategy,
    )"""

NEW_SAVE_CYCLE = """    # Build stock signal dict for cycle log
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
    )"""

if "_stock_signal_log" not in src:
    if OLD_SAVE_CYCLE in src:
        src = src.replace(OLD_SAVE_CYCLE, NEW_SAVE_CYCLE, 1)
        patches.append("✅ PATCH 6 — stock signal logged to cycle log")
    else:
        patches.append("⚠️  SKIP 6 — save_cycle_log anchor not found")
else:
    patches.append("⚠️  SKIP 6 — stock signal already in cycle log")

# ── PATCH 7: Add stock_signal param to save_cycle_log function ────────────────
OLD_SAVE_FN = """def save_cycle_log(cycle_num, consensus_direction, consensus_confidence, llm_rationale="", orderflow_metrics=None, signed_votes=None, strategy=""):"""
NEW_SAVE_FN = """def save_cycle_log(cycle_num, consensus_direction, consensus_confidence, llm_rationale="", orderflow_metrics=None, signed_votes=None, strategy="", stock_signal=None):"""

OLD_CYCLE_ENTRY = '            "strategy": strategy or config.ACTIVE_STRATEGY,'
NEW_CYCLE_ENTRY = '''            "strategy": strategy or config.ACTIVE_STRATEGY,
            "stock_signal": stock_signal or {},'''

if "stock_signal=None" not in src:
    if OLD_SAVE_FN in src:
        src = src.replace(OLD_SAVE_FN, NEW_SAVE_FN, 1)
        patches.append("✅ PATCH 7a — save_cycle_log signature extended")
    else:
        patches.append("⚠️  SKIP 7a — save_cycle_log signature not found")
    if OLD_CYCLE_ENTRY in src:
        src = src.replace(OLD_CYCLE_ENTRY, NEW_CYCLE_ENTRY, 1)
        patches.append("✅ PATCH 7b — stock_signal written to cycle entry")
    else:
        patches.append("⚠️  SKIP 7b — cycle entry anchor not found")
else:
    patches.append("⚠️  SKIP 7 — stock_signal already in save_cycle_log")

# ── WRITE ─────────────────────────────────────────────────────────────────────
TARGET.write_text(src)

print()
for p in patches:
    print(f"  {p}")

skips = sum(1 for p in patches if p.startswith("⚠️"))
applied = len(patches) - skips

print()
if skips == 0:
    print(f"✅ All {applied} patches applied → {TARGET}")
else:
    print(f"✅ {applied} patches applied, {skips} skipped (already present) → {TARGET}")
print(f"🔁 Restore with: cp {BACKUP} {TARGET}")
