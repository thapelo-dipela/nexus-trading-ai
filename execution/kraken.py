"""
Kraken Execution Layer — order placement and portfolio balance only.
No data fetching of any kind belongs here. All market data comes from PRISM.
Multi-pair support with strategy-specific TP/SL and YOLO overrides.
"""
import subprocess
import json
import logging
from typing import Tuple, Dict, Any, List, Optional
 
import config
from agents.base import Candle
 
logger = logging.getLogger(__name__)

# Multi-pair support (Section 6E) — default pairs
DEFAULT_PAIRS = [
    "XBTUSDT", "ETHUSDT", "SOLUSDT", "MATICUSDT", "AVAXUSDT",
    "LINKUSDT", "DOTUSDT", "ADAUSDT", "DOGEUSDT", "XRPUSDT"
]

# Strategy-specific TP/SL percentages (Section 6E)
STRATEGY_TP_SL = {
    "trend_following": {"tp_pct": 8.0, "sl_pct": 3.0},
    "breakout": {"tp_pct": 10.0, "sl_pct": 2.0},
    "mean_reversion": {"tp_pct": 4.0, "sl_pct": 1.5},
    "scalping": {"tp_pct": 1.5, "sl_pct": 0.5},
    "swing": {"tp_pct": 15.0, "sl_pct": 5.0},
    "algorithmic_quant": {"tp_pct": 5.0, "sl_pct": 2.0},  # Default
    "arbitrage": {"tp_pct": 0.5, "sl_pct": 0.2},
    "smc": {"tp_pct": 7.0, "sl_pct": 2.5},
    "position": {"tp_pct": 30.0, "sl_pct": 8.0},
    "yolo": {"tp_pct": 12.0, "sl_pct": 4.0},
}

 
 
class KrakenClient:
    """Kraken CLI execution client with multi-pair and strategy support."""
 
    def __init__(self, cli_path: str = config.KRAKEN_CLI_PATH, pair: str = config.PAIR, dry_run: bool = False, strategy: str = None):
        self.cli_path = cli_path
        self.pair = pair  # Primary trading pair (default for backwards compatibility)
        self.pairs = [pair] + [p for p in DEFAULT_PAIRS if p != pair]  # All available pairs
        self.dry_run = dry_run
        self.strategy = strategy or config.ACTIVE_STRATEGY
        self._dry_run_position_usd: float = 0.0  # Tracks simulated BTC position value
        self._dry_run_positions: Dict[str, float] = {pair: 0.0}  # Multi-pair tracking
        self._yolo_last_sl_hit_time: Dict[str, float] = {}  # YOLO cooldown tracking
        
    def get_strategy_tp_sl(self) -> Tuple[float, float]:
        """Get TP/SL percentages for current strategy."""
        if self.strategy not in STRATEGY_TP_SL:
            self.strategy = "algorithmic_quant"
        tp_pct, sl_pct = STRATEGY_TP_SL[self.strategy]["tp_pct"], STRATEGY_TP_SL[self.strategy]["sl_pct"]
        logger.debug(f"[dim]Strategy {self.strategy}: TP={tp_pct}%, SL={sl_pct}%[/dim]")
        return tp_pct, sl_pct
    
    def calculate_tp_sl_prices(self, entry_price: float, direction: str) -> Tuple[float, float]:
        """
        Calculate take-profit and stop-loss prices based on entry price and strategy.
        
        Args:
            entry_price: Entry price
            direction: "BUY" or "SELL"
            
        Returns:
            (tp_price, sl_price)
        """
        tp_pct, sl_pct = self.get_strategy_tp_sl()
        
        if direction == "BUY":
            tp_price = entry_price * (1.0 + tp_pct / 100.0)
            sl_price = entry_price * (1.0 - sl_pct / 100.0)
        else:  # SELL
            tp_price = entry_price * (1.0 - tp_pct / 100.0)
            sl_price = entry_price * (1.0 + sl_pct / 100.0)
        
        logger.info(
            f"[dim]TP/SL for {direction} @ ${entry_price:,.2f}: "
            f"TP=${tp_price:,.2f}, SL=${sl_price:,.2f}[/dim]"
        )
        return tp_price, sl_price
 
    def market_buy(self, volume: float, entry_price: float = None) -> Dict[str, Any]:
        """
        Execute a market buy order with strategy-specific TP/SL.
        Args:
            volume: Asset volume to buy (not USD)
            entry_price: Entry price (optional, for TP/SL calculation)
        Returns:
            Response dict from Kraken CLI with TP/SL prices
        """
        if self.dry_run:
            price = entry_price or self.get_ticker_price() or 71000.0
            self._dry_run_position_usd += volume * price
            tp_price, sl_price = self.calculate_tp_sl_prices(price, "BUY")
            logger.info(f"[bold green]DRY-RUN BUY {volume} BTC @ ${price:,.2f} (TP=${tp_price:,.2f}, SL=${sl_price:,.2f})[/bold green]")
            return {"status": "dry_run", "volume": volume, "entry_price": price, "tp_price": tp_price, "sl_price": sl_price}
 
        try:
            cmd = [
                self.cli_path,
                "order",
                "buy",
                "--type",
                "market",
                "-o",
                "json",
                self.pair,
                str(volume),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
 
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    # Add TP/SL to response if entry_price provided
                    if entry_price:
                        tp_price, sl_price = self.calculate_tp_sl_prices(entry_price, "BUY")
                        response["tp_price"] = tp_price
                        response["sl_price"] = sl_price
                    logger.info(f"[bold green]Market BUY {volume} {self.pair}: {response}[/bold green]")
                    return response
                except json.JSONDecodeError:
                    logger.error(f"[red]Kraken CLI returned invalid JSON: {result.stdout}[/red]")
                    return {"error": "invalid_json", "raw": result.stdout}
            else:
                logger.error(f"[red]Kraken CLI error: {result.stderr}[/red]")
                return {"error": "cli_error", "stderr": result.stderr}
 
        except subprocess.TimeoutExpired:
            logger.error("[red]Kraken CLI timeout on market_buy[/red]")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"[red]market_buy exception: {e}[/red]")
            return {"error": str(e)}
 
    def market_sell(self, volume: float, entry_price: float = None) -> Dict[str, Any]:
        """
        Execute a market sell order with strategy-specific TP/SL.
        Args:
            volume: Asset volume to sell (not USD)
            entry_price: Entry price (optional, for TP/SL calculation)
        Returns:
            Response dict from Kraken CLI with TP/SL prices
        """
        if self.dry_run:
            price = entry_price or self.get_ticker_price() or 71000.0
            self._dry_run_position_usd = max(0.0, self._dry_run_position_usd - (volume * price))
            tp_price, sl_price = self.calculate_tp_sl_prices(price, "SELL")
            logger.info(f"[bold green]DRY-RUN SELL {volume} BTC @ ${price:,.2f} (TP=${tp_price:,.2f}, SL=${sl_price:,.2f})[/bold green]")
            return {"status": "dry_run", "volume": volume, "entry_price": price, "tp_price": tp_price, "sl_price": sl_price}
 
        try:
            cmd = [
                self.cli_path,
                "order",
                "sell",
                "--type",
                "market",
                "-o",
                "json",
                self.pair,
                str(volume),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
 
            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)
                    # Add TP/SL to response if entry_price provided
                    if entry_price:
                        tp_price, sl_price = self.calculate_tp_sl_prices(entry_price, "SELL")
                        response["tp_price"] = tp_price
                        response["sl_price"] = sl_price
                    logger.info(f"[bold green]Market SELL {volume} {self.pair}: {response}[/bold green]")
                    return response
                except json.JSONDecodeError:
                    logger.error(f"[red]Kraken CLI returned invalid JSON: {result.stdout}[/red]")
                    return {"error": "invalid_json", "raw": result.stdout}
            else:
                logger.error(f"[red]Kraken CLI error: {result.stderr}[/red]")
                return {"error": "cli_error", "stderr": result.stderr}
 
        except subprocess.TimeoutExpired:
            logger.error("[red]Kraken CLI timeout on market_sell[/red]")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"[red]market_sell exception: {e}[/red]")
            return {"error": str(e)}
 
    def portfolio_summary(self) -> Tuple[float, float]:
        """
        Fetch portfolio summary from Kraken.
        Uses: kraken balance -o json
        Returns: (portfolio_value_usd, open_position_usd)
        If query fails, returns (0.0, 0.0) with a single clean warning.
        """
        # In dry-run mode, track simulated positions properly
        if self.dry_run:
            open_pos = self._dry_run_position_usd
            total = 10000.0 + open_pos
            logger.debug(f"[dim]DRY-RUN: Portfolio=${total:.2f} (cash=10000.00, open_pos=${open_pos:.2f})[/dim]")
            return (total, open_pos)
 
        try:
            # Query cash balances: kraken balance -o json
            # Response format: {"ZUSD": "10234.56", "XXBT": "0.0312", ...}
            cmd = [self.cli_path, "balance", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
 
            if result.returncode != 0:
                logger.warning(f"[yellow]Kraken balance command failed[/yellow]")
                return (0.0, 0.0)
 
            try:
                balance_data = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.warning("[yellow]Kraken returned invalid JSON for balance[/yellow]")
                return (0.0, 0.0)
 
            # Extract USD balance (ZUSD is Kraken's USD currency code)
            usd_balance = float(balance_data.get("ZUSD", "0.0"))
 
            # Extract BTC balance if available (XXBT is Kraken's BTC currency code)
            btc_balance = float(balance_data.get("XXBT", "0.0"))
 
            # Calculate BTC position value using current ticker price
            btc_position_usd = 0.0
            if btc_balance > 0:
                try:
                    btc_price = self.get_ticker_price()
                    if btc_price:
                        btc_position_usd = btc_balance * btc_price
                except Exception as e:
                    logger.debug(f"[dim]Could not fetch BTC price for position valuation: {e}[/dim]")
 
            # Total portfolio value = USD + BTC position
            portfolio_value = usd_balance + btc_position_usd
 
            logger.debug(
                f"[dim]Portfolio: ${portfolio_value:.2f} (USD: ${usd_balance:.2f}, BTC: ${btc_position_usd:.2f})[/dim]"
            )
            return (portfolio_value, btc_position_usd)
 
        except subprocess.TimeoutExpired:
            logger.warning("[yellow]Kraken CLI timeout on portfolio_summary[/yellow]")
            return (0.0, 0.0)
        except Exception as e:
            logger.warning(f"[yellow]portfolio_summary exception: {e}[/yellow]")
            return (0.0, 0.0)
 
    def usd_to_volume(self, usd: float, current_price: float) -> float:
        """
        Convert USD amount to asset volume using current PRISM price.
        Args:
            usd: Dollar amount to convert
            current_price: Current asset price from PRISM
        Returns:
            Asset volume
        """
        if current_price <= 0:
            logger.warning("[yellow]Invalid price for USD to volume conversion[/yellow]")
            return 0.0
        return usd / current_price
    
    def get_yolo_position_size(self, requested_usd: float) -> float:
        """
        Get position size, applying YOLO override if active.
        If strategy is "yolo", force max position size to $500 (hard limit).
        
        Args:
            requested_usd: Requested position size in USD
            
        Returns:
            Actual position size to use (capped at max trade size)
        """
        max_size = config.MAX_TRADE_SIZE_USD
        
        if self.strategy == "yolo":
            # YOLO forces $500 maximum per config
            actual_size = min(requested_usd, max_size)
            if actual_size < max_size:
                logger.warning(
                    f"[yellow]🎲 YOLO override: Capping position from ${requested_usd:.2f} to ${max_size:.2f}[/yellow]"
                )
            return actual_size
        
        # Standard strategies respect max trade size but can be smaller
        return min(requested_usd, max_size)
    
    def on_yolo_sl_hit(self, pair: str, timestamp: float) -> None:
        """
        Callback when YOLO position hits stop-loss.
        Triggers 1-hour cooldown before next YOLO activation.
        
        Args:
            pair: Trading pair (e.g., "XBTUSDT")
            timestamp: Unix timestamp of SL hit
        """
        if self.strategy != "yolo":
            return
        
        self._yolo_last_sl_hit_time[pair] = timestamp
        logger.warning(
            f"[yellow]🎲 YOLO SL HIT on {pair}: Cooldown active until {timestamp + 3600}[/yellow]"
        )
    
    def is_yolo_on_cooldown(self, pair: str) -> bool:
        """
        Check if YOLO is on cooldown after hitting SL.
        
        Args:
            pair: Trading pair (e.g., "XBTUSDT")
            
        Returns:
            True if cooldown active, False otherwise
        """
        import time
        
        if self.strategy != "yolo" or pair not in self._yolo_last_sl_hit_time:
            return False
        
        time_since_sl = time.time() - self._yolo_last_sl_hit_time[pair]
        cooldown_seconds = config.YOLO_COOLDOWN_AFTER_SL or 3600  # 1 hour default
        
        is_cooldown = time_since_sl < cooldown_seconds
        if is_cooldown:
            remaining = cooldown_seconds - int(time_since_sl)
            logger.debug(f"[dim]YOLO cooldown: {remaining}s remaining on {pair}[/dim]")
        
        return is_cooldown
    
 
    def get_ticker_price(self) -> Optional[float]:
        """
        Fetch current ticker price from Kraken CLI.
        Command: kraken ticker -o json PAIR
        Returns current price as float or None on failure.
        """
        try:
            cmd = [
                self.cli_path,
                "ticker",
                "-o",
                "json",
                self.pair,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
 
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, dict) and self.pair in data:
                        last_trade_price = float(data[self.pair]["c"][0])
                        return last_trade_price
                    else:
                        logger.error(f"[red]Kraken CLI ticker returned unexpected format: {result.stdout}[/red]")
                        return None
                except (json.JSONDecodeError, KeyError, IndexError, ValueError) as e:
                    logger.error(f"[red]Kraken CLI ticker parsing failed: {e} | Raw: {result.stdout}[/red]")
                    return None
            else:
                logger.error(f"[red]Kraken CLI ticker error: {result.stderr}[/red]")
                return None
 
        except subprocess.TimeoutExpired:
            logger.error("[red]Kraken CLI timeout on get_ticker_price[/red]")
            return None
        except Exception as e:
            logger.error(f"[red]get_ticker_price exception: {e}[/red]")
            return None
 
    def fetch_ohlcv(
        self, symbol: str, interval_minutes: int, limit: int = 100
    ) -> Optional[List[Candle]]:
        """
        Fetch OHLCV candles from Kraken CLI.
        Command: kraken ohlc --interval MINUTES -o json PAIR
        Returns list of Candle objects or None on failure.
        """
        try:
            cmd = [
                self.cli_path,
                "ohlc",
                "--interval",
                str(interval_minutes),
                "-o",
                "json",
                self.pair,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
 
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    if isinstance(data, dict) and self.pair in data:
                        ohlcv_data = data[self.pair]
                        candles = []
                        # Kraken CLI OHLC output format: [timestamp, open, high, low, close, vwap, volume, count]
                        for entry in ohlcv_data[-limit:]:
                            candles.append(
                                Candle(
                                    timestamp=int(entry[0]),
                                    open=float(entry[1]),
                                    high=float(entry[2]),
                                    low=float(entry[3]),
                                    close=float(entry[4]),
                                    volume=float(entry[6]),  # Volume is at index 6
                                )
                            )
                        return candles
                    else:
                        logger.error(f"[red]Kraken CLI OHLCV returned unexpected format: {result.stdout}[/red]")
                        return None
                except json.JSONDecodeError:
                    logger.error(f"[red]Kraken CLI OHLCV returned invalid JSON: {result.stdout}[/red]")
                    return None
            else:
                logger.error(f"[red]Kraken CLI OHLCV error: {result.stderr}[/red]")
                return None
 
        except subprocess.TimeoutExpired:
            logger.error("[red]Kraken CLI timeout on fetch_ohlcv[/red]")
            return None
        except Exception as e:
            logger.error(f"[red]fetch_ohlcv exception: {e}[/red]")
            return None
