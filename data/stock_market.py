"""
StockMarketClient — JSE Top 50 + US Stocks data via Yahoo Finance.
Provides price data, signals, and BTC-relative momentum for the
JSE-vs-BTC cross-asset correlation strategy.

Architecture:
  - Yahoo Finance (yfinance): free, no API key, covers JSE + US
  - JSE symbols use the .JO suffix (e.g. NPN.JO for Naspers)
  - US symbols are standard tickers (AAPL, MSFT, etc.)
  - BTC correlation: compares 30d return of each stock vs BTC
    to generate a relative strength signal for crypto positioning

BTC Correlation Strategy Logic:
  When JSE stocks UNDERPERFORM BTC over 30 days:
    → Capital rotation signal: BTC is stronger, hold/buy crypto
  When JSE stocks OUTPERFORM BTC over 30 days:
    → Risk-off signal: traditional assets attracting capital, reduce crypto

Install: pip install yfinance --break-system-packages
"""

import logging
import time
import math
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    _YF_AVAILABLE = True
except ImportError:
    _YF_AVAILABLE = False
    logger.warning("yfinance not installed — run: pip install yfinance --break-system-packages")

# ---------------------------------------------------------------------------
# JSE Top 50 Symbols (Yahoo Finance .JO suffix)
# ---------------------------------------------------------------------------

JSE_TOP_50: Dict[str, str] = {
    # Mega caps
    "NPN.JO":  "Naspers",
    "PRX.JO":  "Prosus",
    "BHP.JO":  "BHP Group",
    "AGL.JO":  "Anglo American",
    "FSR.JO":  "FirstRand",
    "SBK.JO":  "Standard Bank",
    "ABG.JO":  "Absa Group",
    "NED.JO":  "Nedbank",
    "CPI.JO":  "Capitec Bank",
    "SHP.JO":  "Shoprite",
    # Resources
    "GFI.JO":  "Gold Fields",
    "ANG.JO":  "AngloGold Ashanti",
    "IMP.JO":  "Impala Platinum",
    "NHM.JO":  "Northam Platinum",
    "ARM.JO":  "African Rainbow Minerals",
    "EXX.JO":  "Exxaro Resources",
    "SSW.JO":  "Sibanye Stillwater",
    "AMS.JO":  "Anglo American Platinum",
    "MTX.JO":  "Metair Investments",
    "TGA.JO":  "Thungela Resources",
    # Telecoms & Tech
    "MTN.JO":  "MTN Group",
    "VOD.JO":  "Vodacom Group",
    "TLS.JO":  "Telkom SA",
    "WHL.JO":  "Woolworths Holdings",
    "TFG.JO":  "The Foschini Group",
    # Industrials
    "SOL.JO":  "Sasol",
    "MNP.JO":  "Mondi",
    "SPP.JO":  "Spar Group",
    "PIK.JO":  "Pick n Pay",
    "DSY.JO":  "Discovery",
    # Financial Services
    "RMH.JO":  "RMB Holdings",
    "INL.JO":  "Investec",
    "SLM.JO":  "Sanlam",
    "MMK.JO":  "Momentum Metropolitan",
    "OML.JO":  "Old Mutual",
    "LBH.JO":  "Liberty Holdings",
    "GRT.JO":  "Growthpoint Properties",
    "RDF.JO":  "Redefine Properties",
    "VKE.JO":  "Vukile Property Fund",
    "HYP.JO":  "Hyprop Investments",
    # Consumer & Retail
    "MRP.JO":  "Mr Price Group",
    "TRU.JO":  "Truworths International",
    "BVT.JO":  "Bidvest Group",
    "BAW.JO":  "Barloworld",
    "RBP.JO":  "RB Placements",
    "CFR.JO":  "Compagnie Financière Richemont",
    "AVI.JO":  "AVI Limited",
    "DCP.JO":  "Dis-Chem Pharmacies",
    "CLS.JO":  "Clicks Group",
    "SNH.JO":  "Steinhoff International",
}

# ---------------------------------------------------------------------------
# US Stock symbols (Alpaca paper trading compatible)
# ---------------------------------------------------------------------------

US_TOP_STOCKS: Dict[str, str] = {
    "AAPL":  "Apple",
    "MSFT":  "Microsoft",
    "GOOGL": "Alphabet",
    "AMZN":  "Amazon",
    "NVDA":  "NVIDIA",
    "META":  "Meta Platforms",
    "TSLA":  "Tesla",
    "BRK-B": "Berkshire Hathaway",
    "JPM":   "JPMorgan Chase",
    "V":     "Visa",
    "JNJ":   "Johnson & Johnson",
    "UNH":   "UnitedHealth Group",
    "XOM":   "ExxonMobil",
    "MA":    "Mastercard",
    "PG":    "Procter & Gamble",
    "HD":    "Home Depot",
    "CVX":   "Chevron",
    "MRK":   "Merck",
    "ABBV":  "AbbVie",
    "KO":    "Coca-Cola",
}

# ---------------------------------------------------------------------------
# Internal cache
# ---------------------------------------------------------------------------

@dataclass
class _CacheEntry:
    data: Any
    timestamp: float = field(default_factory=time.time)
    ttl: int = 300  # 5 min default for stock data (slower moving)

    def is_expired(self) -> bool:
        return time.time() - self.timestamp > self.ttl


class _Cache:
    def __init__(self):
        self._store: Dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry and not entry.is_expired():
            return entry.data
        return None

    def set(self, key: str, data: Any, ttl: int = 300):
        self._store[key] = _CacheEntry(data=data, ttl=ttl)


# ---------------------------------------------------------------------------
# BTC Correlation Result
# ---------------------------------------------------------------------------

@dataclass
class BTCCorrelationSignal:
    """
    Cross-asset signal comparing JSE/US stock performance vs BTC.

    btc_return_30d       : BTC 30-day return (%)
    stock_return_30d     : Basket average 30-day return (%)
    relative_strength    : stock_return - btc_return (negative = BTC stronger)
    crypto_signal        : "BUY_CRYPTO" | "HOLD" | "REDUCE_CRYPTO"
    confidence           : 0.0–1.0
    top_performers       : stocks beating BTC (rotation away from crypto)
    underperformers      : stocks lagging BTC (stay in crypto)
    reasoning            : human-readable explanation
    """
    btc_return_30d:    float = 0.0
    stock_return_30d:  float = 0.0
    relative_strength: float = 0.0
    crypto_signal:     str   = "HOLD"
    confidence:        float = 0.0
    top_performers:    List[str] = field(default_factory=list)
    underperformers:   List[str] = field(default_factory=list)
    reasoning:         str   = ""
    timestamp:         float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# StockMarketClient
# ---------------------------------------------------------------------------

class StockMarketClient:
    """
    Unified stock data client for JSE Top 50 and US markets.
    Uses Yahoo Finance (free, no API key required).

    Primary use case for NEXUS:
      btc_correlation_signal() → feeds into SentimentAgent and
      consensus engine as a cross-asset regime signal.
    """

    def __init__(self):
        if not _YF_AVAILABLE:
            raise ImportError(
                "yfinance not installed. Run: "
                "pip install yfinance --break-system-packages"
            )
        self._cache = _Cache()

    # ------------------------------------------------------------------
    # Single stock price
    # ------------------------------------------------------------------

    def get_price(self, ticker: str) -> Optional[Dict]:
        """
        Get current price for any ticker (JSE or US).
        JSE: use .JO suffix (e.g. 'NPN.JO')
        US:  standard ticker (e.g. 'AAPL')

        Returns: {"price": float, "change_24h_pct": float, "currency": str, "name": str}
        """
        cache_key = f"price_{ticker}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            stock = yf.Ticker(ticker)
            info  = stock.info

            price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            )
            if not price:
                logger.warning(f"StockClient: no price for {ticker}")
                return None

            change_pct = info.get("regularMarketChangePercent", 0.0) or 0.0
            currency   = info.get("currency", "USD")
            name       = info.get("longName") or info.get("shortName") or ticker

            result = {
                "price":          float(price),
                "change_24h_pct": float(change_pct),
                "currency":       currency,
                "name":           name,
                "ticker":         ticker,
                "source":         "yahoo_finance",
            }
            self._cache.set(cache_key, result, ttl=300)
            logger.debug(f"Stock price {ticker}: {currency} {price:.2f} ({change_pct:+.2f}%)")
            return result

        except Exception as e:
            logger.warning(f"StockClient: get_price failed for {ticker}: {e}")
            return None

    # ------------------------------------------------------------------
    # Batch prices
    # ------------------------------------------------------------------

    def get_prices_batch(self, tickers: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Fetch prices for multiple tickers in one yfinance call.
        Much faster than individual calls for large batches.
        """
        cache_key = f"batch_{'_'.join(sorted(tickers))}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        results: Dict[str, Optional[Dict]] = {t: None for t in tickers}

        try:
            # yfinance batch download — single HTTP call
            data = yf.download(
                tickers,
                period="2d",
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            if data.empty:
                logger.warning("StockClient: batch download returned empty data")
                return results

            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[ticker] if ticker in data.columns.get_level_values(0) else None

                    if ticker_data is None or ticker_data.empty:
                        continue

                    closes = ticker_data["Close"].dropna()
                    if len(closes) < 1:
                        continue

                    price = float(closes.iloc[-1])
                    change_pct = 0.0
                    if len(closes) >= 2:
                        change_pct = ((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2]) * 100

                    results[ticker] = {
                        "price":          price,
                        "change_24h_pct": round(change_pct, 3),
                        "currency":       "ZAR" if ticker.endswith(".JO") else "USD",
                        "name":           JSE_TOP_50.get(ticker) or US_TOP_STOCKS.get(ticker) or ticker,
                        "ticker":         ticker,
                        "source":         "yahoo_finance",
                    }
                except Exception as e:
                    logger.debug(f"StockClient: batch parse failed for {ticker}: {e}")

        except Exception as e:
            logger.warning(f"StockClient: batch download failed: {e}")

        self._cache.set(cache_key, results, ttl=300)
        fetched = sum(1 for v in results.values() if v is not None)
        logger.info(f"StockClient: batch fetched {fetched}/{len(tickers)} prices")
        return results

    # ------------------------------------------------------------------
    # 30-day returns for a basket of tickers
    # ------------------------------------------------------------------

    def get_30d_returns(self, tickers: List[str]) -> Dict[str, float]:
        """
        Fetch 30-day price return (%) for a list of tickers.
        Returns: {ticker: return_pct}
        """
        cache_key = f"returns30d_{'_'.join(sorted(tickers))}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        returns: Dict[str, float] = {}

        try:
            data = yf.download(
                tickers,
                period="35d",   # 35d to ensure 30 trading days available
                interval="1d",
                group_by="ticker",
                auto_adjust=True,
                progress=False,
                threads=True,
            )

            if data.empty:
                return returns

            for ticker in tickers:
                try:
                    if len(tickers) == 1:
                        closes = data["Close"].dropna()
                    else:
                        closes = data[ticker]["Close"].dropna() if ticker in data.columns.get_level_values(0) else None

                    if closes is None or len(closes) < 2:
                        continue

                    # Use up to 30 days back
                    start_price = float(closes.iloc[max(0, len(closes) - 30)])
                    end_price   = float(closes.iloc[-1])
                    ret = ((end_price - start_price) / start_price) * 100
                    returns[ticker] = round(ret, 3)

                except Exception as e:
                    logger.debug(f"StockClient: return calc failed for {ticker}: {e}")

        except Exception as e:
            logger.warning(f"StockClient: 30d returns download failed: {e}")

        self._cache.set(cache_key, returns, ttl=3600)  # Cache 1 hour
        return returns

    # ------------------------------------------------------------------
    # BTC Correlation Signal — the core cross-asset strategy
    # ------------------------------------------------------------------

    def btc_correlation_signal(
        self,
        btc_return_30d: Optional[float] = None,
        use_jse: bool = True,
        use_us: bool = False,
        top_n: int = 20,
    ) -> BTCCorrelationSignal:
        """
        Core cross-asset signal comparing JSE Top 50 (and/or US stocks)
        against BTC 30-day performance.

        Strategy logic:
          relative_strength = avg_stock_return_30d - btc_return_30d

          If relative_strength < -10%  → BTC dominates → BUY_CRYPTO (high conf)
          If relative_strength < -5%   → BTC leading   → BUY_CRYPTO (moderate)
          If relative_strength > +10%  → Stocks dominate → REDUCE_CRYPTO (high conf)
          If relative_strength > +5%   → Stocks leading  → REDUCE_CRYPTO (moderate)
          Otherwise                    → HOLD

        Args:
            btc_return_30d: Pre-fetched BTC 30d return (%). If None, fetches from Yahoo.
            use_jse:        Include JSE Top 50 in basket (default True)
            use_us:         Include US Top 20 in basket (default False)
            top_n:          Number of JSE stocks to use (max 50)

        Returns:
            BTCCorrelationSignal with crypto positioning recommendation
        """
        cache_key = f"btc_corr_{use_jse}_{use_us}_{top_n}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        signal = BTCCorrelationSignal()

        # 1. Get BTC 30d return
        if btc_return_30d is not None:
            signal.btc_return_30d = btc_return_30d
        else:
            btc_returns = self.get_30d_returns(["BTC-USD"])
            signal.btc_return_30d = btc_returns.get("BTC-USD", 0.0)

        # 2. Build stock basket
        basket: List[str] = []
        if use_jse:
            jse_tickers = list(JSE_TOP_50.keys())[:top_n]
            basket.extend(jse_tickers)
        if use_us:
            basket.extend(list(US_TOP_STOCKS.keys())[:10])

        if not basket:
            signal.reasoning = "No tickers in basket"
            return signal

        # 3. Get stock 30d returns
        stock_returns = self.get_30d_returns(basket)

        if not stock_returns:
            signal.reasoning = "Could not fetch stock returns"
            return signal

        # 4. Compute basket average return (equal-weighted)
        valid_returns = [v for v in stock_returns.values() if v is not None]
        if not valid_returns:
            signal.reasoning = "No valid returns in basket"
            return signal

        signal.stock_return_30d  = round(sum(valid_returns) / len(valid_returns), 3)
        signal.relative_strength = round(signal.stock_return_30d - signal.btc_return_30d, 3)

        # 5. Identify top performers vs underperformers relative to BTC
        signal.top_performers  = [
            t for t, r in stock_returns.items()
            if r is not None and r > signal.btc_return_30d
        ]
        signal.underperformers = [
            t for t, r in stock_returns.items()
            if r is not None and r <= signal.btc_return_30d
        ]

        # 6. Generate crypto positioning signal
        rs = signal.relative_strength
        pct_outperforming = len(signal.top_performers) / max(len(basket), 1)

        if rs < -15.0:
            signal.crypto_signal = "BUY_CRYPTO"
            signal.confidence    = 0.90
        elif rs < -10.0:
            signal.crypto_signal = "BUY_CRYPTO"
            signal.confidence    = 0.75
        elif rs < -5.0:
            signal.crypto_signal = "BUY_CRYPTO"
            signal.confidence    = 0.55
        elif rs > 15.0:
            signal.crypto_signal = "REDUCE_CRYPTO"
            signal.confidence    = 0.90
        elif rs > 10.0:
            signal.crypto_signal = "REDUCE_CRYPTO"
            signal.confidence    = 0.75
        elif rs > 5.0:
            signal.crypto_signal = "REDUCE_CRYPTO"
            signal.confidence    = 0.55
        else:
            signal.crypto_signal = "HOLD"
            signal.confidence    = 0.30

        # Boost confidence if broad consensus (>70% stocks agree)
        if pct_outperforming > 0.70 and signal.crypto_signal == "REDUCE_CRYPTO":
            signal.confidence = min(0.95, signal.confidence + 0.10)
        elif pct_outperforming < 0.30 and signal.crypto_signal == "BUY_CRYPTO":
            signal.confidence = min(0.95, signal.confidence + 0.10)

        signal.reasoning = (
            f"BTC 30d: {signal.btc_return_30d:+.1f}% | "
            f"JSE basket 30d: {signal.stock_return_30d:+.1f}% | "
            f"Relative strength: {rs:+.1f}% | "
            f"{len(signal.top_performers)}/{len(basket)} stocks beat BTC | "
            f"Signal: {signal.crypto_signal} (conf={signal.confidence:.0%})"
        )

        logger.info(f"BTC Correlation: {signal.reasoning}")
        self._cache.set(cache_key, signal, ttl=3600)  # 1 hour cache
        return signal

    # ------------------------------------------------------------------
    # JSE overview for dashboard
    # ------------------------------------------------------------------

    def get_jse_overview(self, top_n: int = 20) -> List[Dict]:
        """
        Get price snapshot of JSE Top N stocks for dashboard display.
        Returns list of dicts with price, change, name, ticker.
        """
        tickers = list(JSE_TOP_50.keys())[:top_n]
        prices  = self.get_prices_batch(tickers)

        overview = []
        for ticker, data in prices.items():
            if data:
                overview.append({
                    "ticker":         ticker,
                    "name":           JSE_TOP_50.get(ticker, ticker),
                    "price":          data["price"],
                    "change_24h_pct": data["change_24h_pct"],
                    "currency":       "ZAR",
                    "category":       "jse_top50",
                })

        overview.sort(key=lambda x: x["change_24h_pct"], reverse=True)
        return overview

    def get_us_overview(self) -> List[Dict]:
        """
        Get price snapshot of US Top stocks for dashboard display.
        """
        tickers = list(US_TOP_STOCKS.keys())
        prices  = self.get_prices_batch(tickers)

        overview = []
        for ticker, data in prices.items():
            if data:
                overview.append({
                    "ticker":         ticker,
                    "name":           US_TOP_STOCKS.get(ticker, ticker),
                    "price":          data["price"],
                    "change_24h_pct": data["change_24h_pct"],
                    "currency":       "USD",
                    "category":       "us_stocks",
                })

        overview.sort(key=lambda x: x["change_24h_pct"], reverse=True)
        return overview
