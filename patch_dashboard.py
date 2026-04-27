#!/usr/bin/env python3
"""
patch_dashboard.py
==================
Patches dashboard_server.py to use FreeMarketClient (CoinGecko + Binance)
for altcoin price and signal data, keeping PRISM only for BTC.

Changes applied:
  1. Import FreeMarketClient and initialise it at startup
  2. /api/market          — BTC price via Binance (reliable 24h change), PRISM for signals/risk
  3. /api/market-overview — all prices via FreeMarketClient.get_prices_batch() (single API call)
  4. /api/risk            — PRISM primary, FreeMarketClient fallback
  5. /api/crypto/<sym>/price   — FreeMarketClient primary, PRISM fallback
  6. /api/crypto/<sym>/signals — FreeMarketClient primary for altcoins, PRISM for BTC

Run once from your project root:
    python3 patch_dashboard.py

A backup is saved as dashboard_server.py.bak before any changes are made.
"""

import re
import shutil
from pathlib import Path

TARGET = Path("dashboard_server.py")
BACKUP = Path("dashboard_server.py.bak")

# ── helpers ──────────────────────────────────────────────────────────────────

def apply(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  ⚠️  SKIP '{label}' — anchor text not found (already patched?)")
        return src
    result = src.replace(old, new, 1)
    print(f"  ✅ PATCH '{label}'")
    return result

# ── load ─────────────────────────────────────────────────────────────────────

src = TARGET.read_text()
shutil.copy(TARGET, BACKUP)
print(f"📦 Backup saved → {BACKUP}\n")

# ── 1. Add FreeMarketClient import + initialisation ───────────────────────────

src = apply(
    src,
    old="from agents.sentiment import fetch_composite_sentiment",
    new=(
        "from agents.sentiment import fetch_composite_sentiment\n"
        "from data.free_market import FreeMarketClient"
    ),
    label="import FreeMarketClient",
)

src = apply(
    src,
    old=(
        "except Exception as e:\n"
        "    logger.error(f\"❌ Failed to initialize PRISM client: {e}\")\n"
        "    prism_client = None"
    ),
    new=(
        "except Exception as e:\n"
        "    logger.error(f\"❌ Failed to initialize PRISM client: {e}\")\n"
        "    prism_client = None\n"
        "\n"
        "# Initialize FreeMarketClient (CoinGecko + Binance — no API key required)\n"
        "try:\n"
        "    free_market = FreeMarketClient()\n"
        "    logger.info(\"✅ FreeMarketClient initialized (CoinGecko + Binance)\")\n"
        "except Exception as e:\n"
        "    logger.error(f\"❌ Failed to initialize FreeMarketClient: {e}\")\n"
        "    free_market = None"
    ),
    label="initialise FreeMarketClient",
)

# ── 2. /api/market — use Binance for BTC price (gives real 24h change) ────────

src = apply(
    src,
    old=(
        "        if prism_client:\n"
        "            # Get price from PRISM\n"
        "            import requests as _req; _btc = _req.get(\"https://api.kraken.com/0/public/Ticker?pair=XBTUSD\", timeout=5).json(); price_data = {\"current_price\": float(list(_btc[\"result\"].values())[0][\"c\"][0]), \"change_24h_pct\": 0, \"volume_24h\": float(list(_btc[\"result\"].values())[0][\"v\"][1])}\n"
        "            \n"
        "            # Get signals\n"
        "            signals_1h = prism_client.get_signals('BTC', '1h')\n"
        "            signals_4h = prism_client.get_signals('BTC', '4h')\n"
        "            \n"
        "            # Get risk\n"
        "            risk = prism_client.get_risk('BTC')\n"
        "            \n"
        "            return jsonify({\n"
        "                'success': True,\n"
        "                'price': price_data.get('current_price', 0),\n"
        "                'change_24h': price_data.get('change_24h_pct', 0),\n"
        "                'volume_24h': price_data.get('volume_24h', 0),\n"
        "                'signal_1h': signals_1h.direction if signals_1h else 'neutral',\n"
        "                'signal_4h': signals_4h.direction if signals_4h else 'neutral',\n"
        "                'risk_score': risk.risk_score if risk else 0,\n"
        "                'timestamp': datetime.now().isoformat()\n"
        "            })\n"
        "        else:\n"
        "            return jsonify({\n"
        "                'success': False,\n"
        "                'error': 'PRISM client not available'\n"
        "            }), 503"
    ),
    new=(
        "        # BTC price: Binance (reliable 24h change + volume)\n"
        "        price_data = free_market.get_price('BTC') if free_market else None\n"
        "\n"
        "        # BTC signals: PRISM primary, FreeMarketClient fallback\n"
        "        signals_1h, signals_4h = None, None\n"
        "        if prism_client:\n"
        "            signals_1h = prism_client.get_signals('BTC', '1h')\n"
        "            signals_4h = prism_client.get_signals('BTC', '4h')\n"
        "        if not signals_1h and free_market:\n"
        "            signals_1h = free_market.get_signals('BTC', '1h')\n"
        "        if not signals_4h and free_market:\n"
        "            signals_4h = free_market.get_signals('BTC', '4h')\n"
        "\n"
        "        # BTC risk: PRISM primary, FreeMarketClient fallback\n"
        "        risk = prism_client.get_risk('BTC') if prism_client else None\n"
        "        if not risk and free_market:\n"
        "            risk = free_market.get_risk('BTC')\n"
        "\n"
        "        if not price_data:\n"
        "            return jsonify({'success': False, 'error': 'Could not fetch BTC price'}), 503\n"
        "\n"
        "        return jsonify({\n"
        "            'success': True,\n"
        "            'price': price_data.get('price', 0),\n"
        "            'change_24h': price_data.get('change_24h_pct', 0),\n"
        "            'volume_24h': price_data.get('volume_24h', 0),\n"
        "            'signal_1h': signals_1h.direction if signals_1h else 'neutral',\n"
        "            'signal_4h': signals_4h.direction if signals_4h else 'neutral',\n"
        "            'risk_score': risk.risk_score if risk else 0,\n"
        "            'source': 'binance+prism',\n"
        "            'timestamp': datetime.now().isoformat()\n"
        "        })"
    ),
    label="/api/market — Binance BTC price + PRISM/free signals",
)

# ── 3. /api/market-overview — FreeMarketClient batch (single API call) ────────

src = apply(
    src,
    old=(
        "    try:\n"
        "        if prism_client:\n"
        "            all_prices = prism_client.get_all_supported_prices()\n"
        "            \n"
        "            # Enrich with symbol metadata\n"
        "            overview = []\n"
        "            for symbol, price_data in all_prices.items():\n"
        "                if symbol in config.SUPPORTED_SYMBOLS:\n"
        "                    meta = config.SUPPORTED_SYMBOLS[symbol]\n"
        "                    overview.append({\n"
        "                        'symbol': symbol,\n"
        "                        'name': meta['name'],\n"
        "                        'category': meta['category'],\n"
        "                        'active': meta['active'],\n"
        "                        'price': price_data.get('price') if price_data else None,\n"
        "                        'change_24h_pct': price_data.get('change_24h_pct') if price_data else None,\n"
        "                        'volume_24h': price_data.get('volume_24h') if price_data else None,\n"
        "                    })\n"
        "            \n"
        "            return jsonify({\n"
        "                'success': True,\n"
        "                'count': len(overview),\n"
        "                'currencies': overview,\n"
        "                'timestamp': datetime.now().isoformat()\n"
        "            })\n"
        "        else:\n"
        "            return jsonify({\n"
        "                'success': False,\n"
        "                'error': 'PRISM client not available'\n"
        "            }), 503"
    ),
    new=(
        "    try:\n"
        "        if not free_market:\n"
        "            return jsonify({'success': False, 'error': 'FreeMarketClient not available'}), 503\n"
        "\n"
        "        # Single batch call — all symbols in one Binance API request\n"
        "        symbols = list(config.SUPPORTED_SYMBOLS.keys())\n"
        "        all_prices = free_market.get_prices_batch(symbols)\n"
        "\n"
        "        overview = []\n"
        "        for symbol, price_data in all_prices.items():\n"
        "            if symbol in config.SUPPORTED_SYMBOLS:\n"
        "                meta = config.SUPPORTED_SYMBOLS[symbol]\n"
        "                overview.append({\n"
        "                    'symbol': symbol,\n"
        "                    'name': meta['name'],\n"
        "                    'category': meta['category'],\n"
        "                    'active': meta['active'],\n"
        "                    'price': price_data.get('price') if price_data else None,\n"
        "                    'change_24h_pct': price_data.get('change_24h_pct') if price_data else None,\n"
        "                    'volume_24h': price_data.get('volume_24h') if price_data else None,\n"
        "                    'source': 'binance',\n"
        "                })\n"
        "\n"
        "        return jsonify({\n"
        "            'success': True,\n"
        "            'count': len(overview),\n"
        "            'currencies': overview,\n"
        "            'timestamp': datetime.now().isoformat()\n"
        "        })"
    ),
    label="/api/market-overview — FreeMarketClient batch",
)

# ── 4. /api/risk — PRISM primary, FreeMarketClient fallback ──────────────────

src = apply(
    src,
    old=(
        "    try:\n"
        "        if prism_client:\n"
        "            risk = prism_client.get_risk('BTC')\n"
        "            if risk:\n"
        "                return jsonify({\n"
        "                    'success': True,\n"
        "                    'risk_score': risk.risk_score,\n"
        "                    'atr_pct': risk.atr_pct,\n"
        "                    'volatility_30d': risk.volatility_30d,\n"
        "                    'max_drawdown_30d': risk.max_drawdown_30d,\n"
        "                    'sharpe_ratio': risk.sharpe_ratio,\n"
        "                    'sortino_ratio': risk.sortino_ratio,\n"
        "                    'timestamp': datetime.now().isoformat()\n"
        "                })\n"
        "        \n"
        "        # Fallback to mock data\n"
        "        return jsonify({\n"
        "            'success': True,\n"
        "            'risk_score': 42.5,\n"
        "            'atr_pct': 1.2,\n"
        "            'volatility_30d': 22.5,\n"
        "            'max_drawdown_30d': 8.3,\n"
        "            'sharpe_ratio': 1.45,\n"
        "            'sortino_ratio': 2.1,\n"
        "            'timestamp': datetime.now().isoformat()\n"
        "        })"
    ),
    new=(
        "    try:\n"
        "        risk = None\n"
        "        source = 'mock'\n"
        "\n"
        "        # Primary: PRISM\n"
        "        if prism_client:\n"
        "            risk = prism_client.get_risk('BTC')\n"
        "            if risk:\n"
        "                source = 'prism'\n"
        "\n"
        "        # Fallback: FreeMarketClient (computed from Binance daily OHLCV)\n"
        "        if not risk and free_market:\n"
        "            risk = free_market.get_risk('BTC')\n"
        "            if risk:\n"
        "                source = 'binance'\n"
        "\n"
        "        if risk:\n"
        "            return jsonify({\n"
        "                'success': True,\n"
        "                'risk_score': risk.risk_score,\n"
        "                'atr_pct': risk.atr_pct,\n"
        "                'volatility_30d': risk.volatility_30d,\n"
        "                'max_drawdown_30d': risk.max_drawdown_30d,\n"
        "                'sharpe_ratio': risk.sharpe_ratio,\n"
        "                'sortino_ratio': risk.sortino_ratio,\n"
        "                'source': source,\n"
        "                'timestamp': datetime.now().isoformat()\n"
        "            })\n"
        "\n"
        "        # Last resort: static fallback so dashboard never breaks\n"
        "        return jsonify({\n"
        "            'success': True,\n"
        "            'risk_score': 42.5,\n"
        "            'atr_pct': 1.2,\n"
        "            'volatility_30d': 22.5,\n"
        "            'max_drawdown_30d': 8.3,\n"
        "            'sharpe_ratio': 1.45,\n"
        "            'sortino_ratio': 2.1,\n"
        "            'source': 'mock',\n"
        "            'timestamp': datetime.now().isoformat()\n"
        "        })"
    ),
    label="/api/risk — PRISM primary + FreeMarketClient fallback",
)

# ── 5. /api/crypto/<sym>/price — FreeMarketClient primary ────────────────────

src = apply(
    src,
    old=(
        "    try:\n"
        "        if prism_client:\n"
        "            symbol_upper = symbol.upper()\n"
        "            price_data = prism_client.get_price(symbol_upper)\n"
        "            \n"
        "            if price_data:\n"
        "                return jsonify({\n"
        "                    'success': True,\n"
        "                    'symbol': symbol_upper,\n"
        "                    'price': price_data.get('price'),\n"
        "                    'change_24h_pct': price_data.get('change_24h_pct'),\n"
        "                    'volume_24h': price_data.get('volume_24h'),\n"
        "                    'timestamp': datetime.now().isoformat()\n"
        "                })\n"
        "            else:\n"
        "                return jsonify({\n"
        "                    'success': False,\n"
        "                    'error': f'Could not fetch price for {symbol_upper}'\n"
        "                }), 404\n"
        "        else:\n"
        "            return jsonify({'success': False, 'error': 'PRISM client not available'}), 503"
    ),
    new=(
        "    try:\n"
        "        symbol_upper = symbol.upper()\n"
        "        price_data = None\n"
        "        source = None\n"
        "\n"
        "        # Primary: FreeMarketClient (Binance)\n"
        "        if free_market:\n"
        "            price_data = free_market.get_price(symbol_upper)\n"
        "            if price_data:\n"
        "                source = 'binance'\n"
        "\n"
        "        # Fallback: PRISM (BTC only, reliably)\n"
        "        if not price_data and prism_client:\n"
        "            price_data = prism_client.get_price(symbol_upper)\n"
        "            if price_data:\n"
        "                source = 'prism'\n"
        "\n"
        "        if price_data:\n"
        "            return jsonify({\n"
        "                'success': True,\n"
        "                'symbol': symbol_upper,\n"
        "                'price': price_data.get('price'),\n"
        "                'change_24h_pct': price_data.get('change_24h_pct'),\n"
        "                'volume_24h': price_data.get('volume_24h'),\n"
        "                'source': source,\n"
        "                'timestamp': datetime.now().isoformat()\n"
        "            })\n"
        "        else:\n"
        "            return jsonify({\n"
        "                'success': False,\n"
        "                'error': f'Could not fetch price for {symbol_upper}'\n"
        "            }), 404"
    ),
    label="/api/crypto/<sym>/price — FreeMarketClient primary",
)

# ── 6. /api/crypto/<sym>/signals — FreeMarketClient for altcoins ─────────────

src = apply(
    src,
    old=(
        "    try:\n"
        "        if prism_client:\n"
        "            symbol_upper = symbol.upper()\n"
        "            timeframe = request.args.get('timeframe', '1h')\n"
        "            \n"
        "            signals = prism_client.get_signals(symbol_upper, timeframe)\n"
        "            \n"
        "            if signals:\n"
        "                return jsonify({\n"
        "                    'success': True,\n"
        "                    'symbol': symbol_upper,\n"
        "                    'timeframe': timeframe,\n"
        "                    'direction': signals.direction,\n"
        "                    'confidence': signals.confidence,\n"
        "                    'score': signals.score,\n"
        "                    'reasoning': signals.reasoning,\n"
        "                    'indicators': signals.indicators,\n"
        "                    'current_price': signals.current_price,\n"
        "                    'timestamp': datetime.now().isoformat()\n"
        "                })\n"
        "            else:\n"
        "                return jsonify({\n"
        "                    'success': False,\n"
        "                    'error': f'Could not fetch signals for {symbol_upper}'\n"
        "                }), 404\n"
        "        else:\n"
        "            return jsonify({'success': False, 'error': 'PRISM client not available'}), 503"
    ),
    new=(
        "    try:\n"
        "        symbol_upper = symbol.upper()\n"
        "        timeframe = request.args.get('timeframe', '1h')\n"
        "        signals = None\n"
        "        source = None\n"
        "\n"
        "        # BTC: PRISM primary (best signal quality), FreeMarketClient fallback\n"
        "        # Altcoins: FreeMarketClient primary (avoids PRISM rate limits)\n"
        "        if symbol_upper == 'BTC' and prism_client:\n"
        "            signals = prism_client.get_signals(symbol_upper, timeframe)\n"
        "            if signals:\n"
        "                source = 'prism'\n"
        "\n"
        "        if not signals and free_market:\n"
        "            signals = free_market.get_signals(symbol_upper, timeframe)\n"
        "            if signals:\n"
        "                source = 'binance'\n"
        "\n"
        "        if signals:\n"
        "            return jsonify({\n"
        "                'success': True,\n"
        "                'symbol': symbol_upper,\n"
        "                'timeframe': timeframe,\n"
        "                'direction': signals.direction,\n"
        "                'confidence': signals.confidence,\n"
        "                'score': signals.score,\n"
        "                'reasoning': signals.reasoning,\n"
        "                'indicators': signals.indicators,\n"
        "                'current_price': signals.current_price,\n"
        "                'source': source,\n"
        "                'timestamp': datetime.now().isoformat()\n"
        "            })\n"
        "        else:\n"
        "            return jsonify({\n"
        "                'success': False,\n"
        "                'error': f'Could not fetch signals for {symbol_upper}'\n"
        "            }), 404"
    ),
    label="/api/crypto/<sym>/signals — PRISM for BTC, FreeMarketClient for altcoins",
)

# ── 7. Update health endpoint to report FreeMarketClient status ───────────────

src = apply(
    src,
    old=(
        "    return jsonify({\n"
        "        'status': 'healthy',\n"
        "        'timestamp': datetime.now().isoformat(),\n"
        "        'prism_connected': prism_client is not None,\n"
        "    })"
    ),
    new=(
        "    return jsonify({\n"
        "        'status': 'healthy',\n"
        "        'timestamp': datetime.now().isoformat(),\n"
        "        'prism_connected': prism_client is not None,\n"
        "        'free_market_connected': free_market is not None,\n"
        "    })"
    ),
    label="/api/health — add free_market_connected flag",
)

# ── write ─────────────────────────────────────────────────────────────────────

TARGET.write_text(src)
print(f"\n✅ Patch complete → {TARGET}")
print("   Run: python3 dashboard_server.py")
