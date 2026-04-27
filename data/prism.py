"""
PRISM API Client — canonical data backbone with per-endpoint TTL caching.
Implements confirmed live API response shapes from curl tests.
"""
import logging
import requests
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import concurrent.futures

import config
from agents.base import Candle, PrismSignal, PrismRisk
from execution.kraken import KrakenClient

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Single cache entry with TTL."""
    data: Any
    timestamp: int = field(default_factory=lambda: int(time.time()))
    ttl: int = 60  # seconds

    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return int(time.time()) - self.timestamp > self.ttl


class PrismClient:
    """PRISM API client with per-endpoint TTL caching."""

    def __init__(self, api_key: str, kraken_client: KrakenClient):
        self.api_key = api_key
        self.base_url = config.PRISM_API_BASE_URL
        self.cache: Dict[str, CacheEntry] = {}
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        self.kraken_client = kraken_client

    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make an HTTP GET request to PRISM.
        Detects 429 rate limit and backs off before returning None.
        Returns None and logs warning if request fails.
        """
        try:
            url = f"{self.base_url}{endpoint}"
            response = self.session.get(url, params=params, timeout=10)
            
            # Detect 429 rate limit and wait before fallback
            if response.status_code == 429:
                logger.warning(f"[yellow]PRISM rate limit hit on {endpoint} — waiting 5s[/yellow]")
                time.sleep(5)
                return None
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"[yellow]PRISM request failed: {e} — using fallback[/yellow]")
            return None

    def _cache_get(self, key: str) -> Optional[Any]:
        """Retrieve from cache if valid."""
        if key in self.cache and not self.cache[key].is_expired():
            return self.cache[key].data
        return None

    def _cache_set(self, key: str, data: Any, ttl: int):
        """Store in cache with TTL."""
        self.cache[key] = CacheEntry(data=data, ttl=ttl)

    def resolve_asset(self, asset: str) -> Optional[Dict]:
        """
        GET /resolve/{asset}
        Resolves any ticker, symbol, or contract address to canonical PRISM ID.
        Returns: {"object": "resolved_asset", "id": "...", "symbol": "BTC", "name": "Bitcoin", ...}
        Cache TTL: 1 hour per asset.
        """
        cache_key = f"resolve_{asset}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        result = self._make_request(f"/resolve/{asset}")
        if result:
            self._cache_set(cache_key, result, config.PRISM_CACHE_TTL_RESOLVE)
            return result
        return None

    def get_price(self, symbol: str) -> Optional[Dict]:
        """
        Get price from GET /signals/{symbol}.
        The /crypto/{symbol}/price endpoint does NOT exist.
        Price comes from data[0]["current_price"] in the signals response.
        Cache TTL: 15 seconds.
        
        Returns: {"price": float, "change_24h_pct": 0.0, "volume_24h": 0.0}
        (change_24h and volume_24h default to 0.0 as PRISM signals does not provide them)
        """
        cache_key = f"price_{symbol}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        # Get price from signals endpoint
        try:
            signals_result = self._make_request(f"/signals/{symbol}")
            if signals_result and "data" in signals_result and len(signals_result["data"]) > 0:
                signal_data = signals_result["data"][0]
                current_price = signal_data.get("current_price")
                if current_price is not None:
                    price_data = {
                        "price": float(current_price),
                        "change_24h_pct": 0.0,  # Not available in PRISM signals
                        "volume_24h": 0.0,      # Not available in PRISM signals
                    }
                    self._cache_set(cache_key, price_data, config.PRISM_CACHE_TTL_PRICE)
                    return price_data
        except Exception as e:
            logger.warning(f"[yellow]Failed to extract price from PRISM signals: {e}[/yellow]")

        logger.warning(f"[yellow]PRISM price extraction failed for {symbol}, trying Kraken CLI fallback[/yellow]")
        
        # Fallback to Kraken CLI ticker
        try:
            kraken_price = self.kraken_client.get_ticker_price()
            if kraken_price:
                price_data = {
                    "price": float(kraken_price),
                    "change_24h_pct": 0.0,
                    "volume_24h": 0.0,
                }
                self._cache_set(cache_key, price_data, config.PRISM_CACHE_TTL_PRICE)
                return price_data
        except Exception as e:
            logger.warning(f"[yellow]Kraken CLI fallback also failed: {e}[/yellow]")

        return None

    def get_prices_batch(self, symbols: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Get prices for multiple symbols efficiently.
        Returns: {symbol: {"price": float, "change_24h_pct": float, "volume_24h": float}, ...}
        """
        prices = {}
        for symbol in symbols:
            prices[symbol] = self.get_price(symbol)
        return prices

    def get_all_supported_prices(self) -> Dict[str, Optional[Dict]]:
        """
        Get prices for all supported symbols from config.
        Returns: {symbol: {price data}, ...}
        """
        cache_key = "all_prices_snapshot"
        cached = self._cache_get(cache_key)
        if cached:
            return cached
        
        symbols = list(config.SUPPORTED_SYMBOLS.keys())
        prices = self.get_prices_batch(symbols)
        
        # Cache the batch for 30 seconds
        self._cache_set(cache_key, prices, config.MULTI_SYMBOL_CACHE_TTL)
        return prices

    def get_signals(self, symbol: str, timeframe: str = "1h") -> Optional[PrismSignal]:
        """
        GET /signals/{symbol}
        Returns: {
          "object": "list",
          "data": [{
            "symbol": "BTC",
            "overall_signal": "neutral"|"bullish"|"bearish"|"strong_bullish"|"strong_bearish",
            "direction": "neutral",
            "strength": "weak"|"moderate"|"strong",
            "bullish_score": 1, "bearish_score": 1, "net_score": 0,
            "current_price": 73175.07,
            "indicators": {"rsi": 75.28, "macd": 1103.96, "macd_histogram": 34.06, ...},
            "active_signals": [...],
            "signal_count": 2,
            "timestamp": "2026-04-10T22:14:48Z"
          }],
          "request_id": "req_..."
        }
        
        Cache TTL: 2 minutes.
        Note: PRISM does not support timeframe parameter — same endpoint always called.
        
        Returns strongly typed PrismSignal or None on failure.
        """
        cache_key = f"signal_{symbol}_{timeframe}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            result = self._make_request(f"/signals/{symbol}")
            if result and "data" in result and len(result["data"]) > 0:
                data = result["data"][0]
                
                # Extract direction (use overall_signal if direction not present)
                direction = data.get("direction") or data.get("overall_signal", "neutral")
                
                # Calculate confidence: abs(net_score) / max(signal_count, 1), clamped to [0.0, 1.0]
                net_score = data.get("net_score", 0)
                signal_count = data.get("signal_count", 1)
                confidence = min(1.0, max(0.0, abs(net_score) / max(signal_count, 1)))
                
                # Calculate score: net_score / max(signal_count, 1), clamped to [-1.0, 1.0]
                score = min(1.0, max(-1.0, net_score / max(signal_count, 1)))
                
                # Build reasoning from strength and active_signals
                strength = data.get("strength", "weak")
                active_signals = data.get("active_signals", [])
                signal_list = "; ".join([f"{s.get('type', 'unknown')}={s.get('signal', '?')}" for s in active_signals])
                reasoning = f"strength={strength}, signals=[{signal_list}]"
                
                # Extract indicators
                indicators = data.get("indicators", {})
                
                # Extract current price
                current_price = float(data.get("current_price", 0.0))
                
                # Extract RSI and MACD histogram for convenience
                rsi = float(indicators.get("rsi", 0.0))
                macd_histogram = float(indicators.get("macd_histogram", 0.0))
                
                signal = PrismSignal(
                    direction=direction,
                    confidence=confidence,
                    score=score,
                    reasoning=reasoning,
                    indicators=indicators,
                    current_price=current_price,
                    rsi=rsi,
                    macd_histogram=macd_histogram,
                )
                self._cache_set(cache_key, signal, config.PRISM_CACHE_TTL_SIGNALS)
                return signal
        except Exception as e:
            logger.warning(f"[yellow]Failed to parse PRISM signal: {e}[/yellow]")
        
        return None

    def get_risk(self, symbol: str) -> Optional[PrismRisk]:
        """
        GET /risk/{symbol}
        Returns: {
          "object": "stats",
          "symbol": "BTC",
          "period_days": 90,
          "daily_volatility": 0.5562,
          "annual_volatility": 8.83,
          "sharpe_ratio": -0.801,
          "sortino_ratio": -0.779,
          "max_drawdown": 35.59,
          "current_drawdown": 0.08,
          "avg_daily_return": -0.0082,
          "positive_days_pct": 49.6,
          "timestamp": "2026-04-10T22:10:23Z"
        }
        
        Cache TTL: 5 minutes.
        Uses threading timeout as belt-and-suspenders for SSL hangs on macOS Python 3.9.
        
        Field mapping:
        - risk_score: computed as min(100, max(0, max_drawdown * 2 + annual_volatility))
        - atr_pct: daily_volatility (already a percentage)
        - volatility_30d: annual_volatility
        - max_drawdown_30d: max_drawdown
        - sharpe_ratio: sharpe_ratio
        - sortino_ratio: sortino_ratio
        - current_drawdown: current_drawdown
        
        Returns strongly typed PrismRisk or None on failure (falls back to local ATR).
        """
        cache_key = f"risk_{symbol}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            # Use threading timeout as belt-and-suspenders against SSL hangs
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._make_request, f"/risk/{symbol}")
                result = future.result(timeout=8)  # 8-second hard wall-clock timeout
            
            if result:
                max_drawdown = float(result.get("max_drawdown", 0.0))
                annual_volatility = float(result.get("annual_volatility", 0.0))
                daily_volatility = float(result.get("daily_volatility", 0.0))
                sharpe_ratio = float(result.get("sharpe_ratio", 0.0))
                sortino_ratio = float(result.get("sortino_ratio", 0.0))
                current_drawdown = float(result.get("current_drawdown", 0.0))
                
                # Compute risk_score: proxy based on max_drawdown and annual_volatility
                risk_score = min(100.0, max(0.0, max_drawdown * 2 + annual_volatility))
                
                risk = PrismRisk(
                    risk_score=risk_score,
                    atr_pct=daily_volatility,
                    volatility_30d=annual_volatility,
                    max_drawdown_30d=max_drawdown,
                    sharpe_ratio=sharpe_ratio,
                    sortino_ratio=sortino_ratio,
                    current_drawdown=current_drawdown,
                )
                self._cache_set(cache_key, risk, config.PRISM_CACHE_TTL_RISK)
                return risk
        except concurrent.futures.TimeoutError:
            logger.warning("[yellow]PRISM /risk timeout (8s) — using fallback risk values[/yellow]")
            return None
        except Exception as e:
            logger.warning(f"[yellow]Failed to parse PRISM risk: {e}[/yellow]")
        
        return None

    def get_ohlcv(
        self, symbol: str, interval_minutes: int, limit: int = 100
    ) -> Optional[List[Candle]]:
        """
        Fetch OHLCV candles from Kraken CLI only.
        PRISM OHLCV endpoint is skipped.
        
        Returns list of Candle objects or None on failure.
        """
        cache_key = f"ohlcv_{symbol}_{interval_minutes}_{limit}"
        cached = self._cache_get(cache_key)
        if cached:
            return cached

        try:
            kraken_candles = self.kraken_client.fetch_ohlcv(symbol, interval_minutes, limit)
            if kraken_candles:
                logger.debug(f"[dim]OHLCV: {len(kraken_candles)} candles via Kraken CLI[/dim]")
                self._cache_set(cache_key, kraken_candles, config.PRISM_CACHE_TTL_PRICE)
                return kraken_candles
        except Exception as e:
            logger.error(f"[red]Kraken CLI OHLCV fetch failed: {e}[/red]")

        return None
