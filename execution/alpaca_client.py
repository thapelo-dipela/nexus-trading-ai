"""
AlpacaClient — US Stock Paper Trading via Alpaca Markets API.
Mirrors KrakenClient's interface for drop-in use in the execution layer.

Paper trading (no real money):
  - Sign up free at https://alpaca.markets
  - Generate paper API keys in the dashboard
  - Set ALPACA_API_KEY and ALPACA_API_SECRET in your .env

Live trading:
  - Requires a funded Alpaca brokerage account
  - Set ALPACA_LIVE=true in .env to switch from paper to live endpoint

Install: pip install alpaca-py --break-system-packages
"""

import logging
import os
import time
from typing import Optional, Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Alpaca endpoints
ALPACA_PAPER_BASE = "https://paper-api.alpaca.markets"
ALPACA_LIVE_BASE  = "https://api.alpaca.markets"
ALPACA_DATA_BASE  = "https://data.alpaca.markets"

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    _ALPACA_AVAILABLE = True
except ImportError:
    _ALPACA_AVAILABLE = False
    logger.warning(
        "alpaca-py not installed — run: "
        "pip install alpaca-py --break-system-packages"
    )


class AlpacaClient:
    """
    US Stock execution via Alpaca paper/live trading.
    Mirrors KrakenClient's market_buy / market_sell interface.

    Environment variables:
      ALPACA_API_KEY    — API key from alpaca.markets dashboard
      ALPACA_API_SECRET — API secret
      ALPACA_LIVE       — set to 'true' for live trading (default: paper)
    """

    def __init__(self):
        self.api_key    = os.environ.get("ALPACA_API_KEY", "")
        self.api_secret = os.environ.get("ALPACA_API_SECRET", "")
        self.is_live    = os.environ.get("ALPACA_LIVE", "false").lower() == "true"
        self.base_url   = ALPACA_LIVE_BASE if self.is_live else ALPACA_PAPER_BASE

        if not self.api_key or not self.api_secret:
            logger.warning(
                "AlpacaClient: ALPACA_API_KEY / ALPACA_API_SECRET not set. "
                "Get free paper keys at https://alpaca.markets"
            )
            self._trading_client = None
            self._data_client    = None
            return

        if not _ALPACA_AVAILABLE:
            logger.error("AlpacaClient: alpaca-py not installed")
            self._trading_client = None
            self._data_client    = None
            return

        try:
            self._trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=not self.is_live,
            )
            self._data_client = StockHistoricalDataClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
            )
            mode = "LIVE" if self.is_live else "PAPER"
            logger.info(f"✅ AlpacaClient initialized ({mode} mode)")
        except Exception as e:
            logger.error(f"AlpacaClient init failed: {e}")
            self._trading_client = None
            self._data_client    = None

    @property
    def is_ready(self) -> bool:
        return self._trading_client is not None

    # ------------------------------------------------------------------
    # Account info
    # ------------------------------------------------------------------

    def get_account(self) -> Optional[Dict]:
        """Get Alpaca account info (buying power, equity, etc.)"""
        if not self.is_ready:
            return None
        try:
            account = self._trading_client.get_account()
            return {
                "equity":        float(account.equity),
                "buying_power":  float(account.buying_power),
                "cash":          float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "currency":      account.currency,
                "status":        account.status,
            }
        except Exception as e:
            logger.error(f"AlpacaClient: get_account failed: {e}")
            return None

    def portfolio_summary(self) -> Tuple[float, float]:
        """
        Mirror KrakenClient.portfolio_summary() interface.
        Returns (portfolio_value_usd, open_position_usd).
        """
        account = self.get_account()
        if not account:
            return 0.0, 0.0

        portfolio_value = account["portfolio_value"]
        open_position   = portfolio_value - account["cash"]
        return portfolio_value, max(0.0, open_position)

    # ------------------------------------------------------------------
    # Market orders — mirror KrakenClient interface
    # ------------------------------------------------------------------

    def market_buy(
        self,
        symbol: str,
        notional_usd: float,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a market buy order for a US stock.

        Args:
            symbol:       Stock ticker (e.g. 'AAPL', 'MSFT')
            notional_usd: Dollar amount to buy (fractional shares supported)
            dry_run:      If True, log without placing order

        Returns:
            Order response dict
        """
        if dry_run:
            logger.info(
                f"[DRY-RUN] Alpaca BUY ${notional_usd:.2f} of {symbol}"
            )
            return {
                "status":   "dry_run",
                "symbol":   symbol,
                "notional": notional_usd,
                "side":     "buy",
            }

        if not self.is_ready:
            return {"error": "AlpacaClient not initialized"}

        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                notional=round(notional_usd, 2),  # Dollar amount (fractional)
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY,
            )
            order = self._trading_client.submit_order(order_request)
            logger.info(
                f"✅ Alpaca BUY ${notional_usd:.2f} {symbol} | "
                f"order_id={order.id} status={order.status}"
            )
            return {
                "status":   str(order.status),
                "order_id": str(order.id),
                "symbol":   symbol,
                "notional": notional_usd,
                "side":     "buy",
            }
        except Exception as e:
            logger.error(f"AlpacaClient: market_buy failed for {symbol}: {e}")
            return {"error": str(e)}

    def market_sell(
        self,
        symbol: str,
        notional_usd: float,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Place a market sell order for a US stock.

        Args:
            symbol:       Stock ticker (e.g. 'AAPL')
            notional_usd: Dollar amount to sell
            dry_run:      If True, log without placing order

        Returns:
            Order response dict
        """
        if dry_run:
            logger.info(
                f"[DRY-RUN] Alpaca SELL ${notional_usd:.2f} of {symbol}"
            )
            return {
                "status":   "dry_run",
                "symbol":   symbol,
                "notional": notional_usd,
                "side":     "sell",
            }

        if not self.is_ready:
            return {"error": "AlpacaClient not initialized"}

        try:
            order_request = MarketOrderRequest(
                symbol=symbol,
                notional=round(notional_usd, 2),
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
            order = self._trading_client.submit_order(order_request)
            logger.info(
                f"✅ Alpaca SELL ${notional_usd:.2f} {symbol} | "
                f"order_id={order.id} status={order.status}"
            )
            return {
                "status":   str(order.status),
                "order_id": str(order.id),
                "symbol":   symbol,
                "notional": notional_usd,
                "side":     "sell",
            }
        except Exception as e:
            logger.error(f"AlpacaClient: market_sell failed for {symbol}: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Positions
    # ------------------------------------------------------------------

    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        if not self.is_ready:
            return []
        try:
            positions = self._trading_client.get_all_positions()
            return [
                {
                    "symbol":      p.symbol,
                    "qty":         float(p.qty),
                    "market_value": float(p.market_value),
                    "cost_basis":  float(p.cost_basis),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc),
                    "current_price": float(p.current_price),
                    "side":        p.side,
                }
                for p in positions
            ]
        except Exception as e:
            logger.error(f"AlpacaClient: get_positions failed: {e}")
            return []

    def close_position(self, symbol: str, dry_run: bool = False) -> Dict:
        """Close entire position for a symbol."""
        if dry_run:
            logger.info(f"[DRY-RUN] Alpaca close position: {symbol}")
            return {"status": "dry_run", "symbol": symbol}

        if not self.is_ready:
            return {"error": "AlpacaClient not initialized"}

        try:
            response = self._trading_client.close_position(symbol)
            logger.info(f"✅ Alpaca closed position: {symbol}")
            return {"status": "closed", "symbol": symbol, "order_id": str(response.id)}
        except Exception as e:
            logger.error(f"AlpacaClient: close_position failed for {symbol}: {e}")
            return {"error": str(e)}

    def get_latest_price(self, symbol: str) -> Optional[float]:
        """Get latest quote price for a US stock."""
        if not self._data_client:
            return None
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote   = self._data_client.get_stock_latest_quote(request)
            if symbol in quote:
                return float(quote[symbol].ask_price or quote[symbol].bid_price)
        except Exception as e:
            logger.warning(f"AlpacaClient: get_latest_price failed for {symbol}: {e}")
        return None

    def is_market_open(self) -> bool:
        """Check if US market is currently open."""
        if not self.is_ready:
            return False
        try:
            clock = self._trading_client.get_clock()
            return clock.is_open
        except Exception:
            return False
