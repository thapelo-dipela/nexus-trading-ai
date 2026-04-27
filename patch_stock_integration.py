#!/usr/bin/env python3
"""
patch_stock_integration.py
==========================
Wires JSE Top 50 + US stocks + BTC correlation signal into NEXUS.

Changes applied:
  1. config.py
     - Adds ALPACA_API_KEY, ALPACA_API_SECRET, ALPACA_LIVE env vars
     - Adds JSE_ENABLED, US_STOCKS_ENABLED, BTC_CORRELATION_ENABLED flags
     - Adds BTC_CORRELATION_THRESHOLD for signal sensitivity
     - Adds Sepolia testnet token pair list for multi-coin testnet trading

  2. dashboard_server.py
     - Initialises StockMarketClient and AlpacaClient at startup
     - Adds GET /api/stocks/jse          → JSE Top 50 overview
     - Adds GET /api/stocks/us           → US stocks overview
     - Adds GET /api/stocks/btc-signal   → BTC correlation signal
     - Adds GET /api/stocks/alpaca       → Alpaca account + positions
     - Updates /api/health to include stock client status

Run from project root:
    python3 patch_stock_integration.py
"""

import shutil
from pathlib import Path

# ── helpers ──────────────────────────────────────────────────────────────────

def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def save(path: Path, content: str):
    path.write_text(content, encoding="utf-8")

def backup(path: Path):
    bak = path.with_suffix(path.suffix + ".bak2")
    shutil.copy(path, bak)
    print(f"  📦 Backup → {bak}")

def apply(src: str, old: str, new: str, label: str) -> str:
    if old not in src:
        print(f"  ⚠️  SKIP '{label}' — anchor not found (already patched?)")
        return src
    result = src.replace(old, new, 1)
    print(f"  ✅ PATCH '{label}'")
    return result

def append_before(src: str, anchor: str, new_block: str, label: str) -> str:
    if anchor not in src:
        print(f"  ⚠️  SKIP '{label}' — anchor not found")
        return src
    result = src.replace(anchor, new_block + "\n" + anchor, 1)
    print(f"  ✅ PATCH '{label}'")
    return result

# ═════════════════════════════════════════════════════════════════════════════
# PATCH 1 — config.py
# ═════════════════════════════════════════════════════════════════════════════

CONFIG = Path("config.py")

if not CONFIG.exists():
    print(f"❌ {CONFIG} not found — skipping")
else:
    print(f"\n📄 Patching {CONFIG}")
    backup(CONFIG)
    src = load(CONFIG)

    # ── 1a: Add Alpaca + Stock config after Etherscan section ────────────────
    src = apply(
        src,
        old="# Etherscan API (for audit trail links - Sepolia)",
        new="""# ─────────────────────────────────────────────────────────────────────────────
# Stock Trading Configuration
# ─────────────────────────────────────────────────────────────────────────────

# Alpaca Paper/Live Trading (US Stocks)
# Get free paper keys at: https://alpaca.markets
ALPACA_API_KEY    = os.getenv("ALPACA_API_KEY", "")
ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET", "")
ALPACA_LIVE       = os.getenv("ALPACA_LIVE", "false").lower() == "true"

# Feature flags — enable/disable per asset class
JSE_ENABLED              = os.getenv("JSE_ENABLED", "true").lower() == "true"
US_STOCKS_ENABLED        = os.getenv("US_STOCKS_ENABLED", "true").lower() == "true"
BTC_CORRELATION_ENABLED  = os.getenv("BTC_CORRELATION_ENABLED", "true").lower() == "true"

# BTC Correlation Strategy
# Relative strength threshold (%) to trigger a crypto signal
# e.g. 5.0 means JSE must lag BTC by 5%+ to trigger BUY_CRYPTO
BTC_CORRELATION_THRESHOLD    = float(os.getenv("BTC_CORRELATION_THRESHOLD", "5.0"))
BTC_CORRELATION_LOOKBACK_DAYS = int(os.getenv("BTC_CORRELATION_LOOKBACK_DAYS", "30"))

# JSE config
JSE_TOP_N = int(os.getenv("JSE_TOP_N", "20"))  # How many JSE stocks to track

# Sepolia Testnet Token Pairs
# These are string labels for the RiskRouter pair field.
# The contract records intent on-chain — it does not move real tokens.
# Sepolia ERC-20 test tokens can be obtained from:
#   https://faucets.chain.link (LINK tokens on Sepolia)
#   https://sepoliafaucet.com  (ETH for gas)
SEPOLIA_TEST_PAIRS = [
    "WBTC/USDC",   # Wrapped BTC testnet
    "WETH/USDC",   # Wrapped ETH testnet
    "WSOL/USDC",   # Wrapped SOL testnet
    "LINK/ETH",    # Chainlink testnet
    "WMATIC/USDC", # Polygon testnet
    "WAVAX/USDC",  # Avalanche testnet
    "WBNB/USDC",   # BNB testnet
    "WDOGE/USDC",  # Dogecoin testnet
    "ARB/ETH",     # Arbitrum testnet
    "OP/ETH",      # Optimism testnet
]

# Primary Sepolia pair for on-chain submission (maps to NEXUS primary symbol)
SEPOLIA_PRIMARY_PAIR = os.getenv("SEPOLIA_PRIMARY_PAIR", "WBTC/USDC")

# Etherscan API (for audit trail links - Sepolia)""",
        label="config.py — add stock trading + Sepolia multi-pair config",
    )

    save(CONFIG, src)
    print(f"  ✅ {CONFIG} saved\n")


# ═════════════════════════════════════════════════════════════════════════════
# PATCH 2 — dashboard_server.py
# ═════════════════════════════════════════════════════════════════════════════

DASHBOARD = Path("dashboard_server.py")

if not DASHBOARD.exists():
    print(f"❌ {DASHBOARD} not found — skipping")
else:
    print(f"📄 Patching {DASHBOARD}")
    backup(DASHBOARD)
    src = load(DASHBOARD)

    # ── 2a: Add stock imports after FreeMarketClient import ──────────────────
    src = apply(
        src,
        old="from data.free_market import FreeMarketClient",
        new=(
            "from data.free_market import FreeMarketClient\n"
            "from data.stock_market import StockMarketClient\n"
            "from execution.alpaca_client import AlpacaClient"
        ),
        label="dashboard_server — import StockMarketClient + AlpacaClient",
    )

    # ── 2b: Initialise stock clients at startup ───────────────────────────────
    src = apply(
        src,
        old=(
            "# Initialize FreeMarketClient (CoinGecko + Binance — no API key required)\n"
            "try:\n"
            "    free_market = FreeMarketClient()\n"
            "    logger.info(\"✅ FreeMarketClient initialized (CoinGecko + Binance)\")\n"
            "except Exception as e:\n"
            "    logger.error(f\"❌ Failed to initialize FreeMarketClient: {e}\")\n"
            "    free_market = None"
        ),
        new=(
            "# Initialize FreeMarketClient (CoinGecko + Binance — no API key required)\n"
            "try:\n"
            "    free_market = FreeMarketClient()\n"
            "    logger.info(\"✅ FreeMarketClient initialized (CoinGecko + Binance)\")\n"
            "except Exception as e:\n"
            "    logger.error(f\"❌ Failed to initialize FreeMarketClient: {e}\")\n"
            "    free_market = None\n"
            "\n"
            "# Initialize StockMarketClient (Yahoo Finance — JSE Top 50 + US stocks)\n"
            "try:\n"
            "    stock_market = StockMarketClient()\n"
            "    logger.info(\"✅ StockMarketClient initialized (Yahoo Finance — JSE + US)\")\n"
            "except Exception as e:\n"
            "    logger.warning(f\"⚠️  StockMarketClient unavailable: {e} (install yfinance)\")\n"
            "    stock_market = None\n"
            "\n"
            "# Initialize AlpacaClient (paper trading — US stocks)\n"
            "try:\n"
            "    alpaca_client = AlpacaClient()\n"
            "    if alpaca_client.is_ready:\n"
            "        logger.info(\"✅ AlpacaClient initialized (paper trading)\")\n"
            "    else:\n"
            "        logger.info(\"⚠️  AlpacaClient: set ALPACA_API_KEY + ALPACA_API_SECRET in .env\")\n"
            "except Exception as e:\n"
            "    logger.warning(f\"⚠️  AlpacaClient unavailable: {e}\")\n"
            "    alpaca_client = None"
        ),
        label="dashboard_server — initialise StockMarketClient + AlpacaClient",
    )

    # ── 2c: Add stock API routes before the error handlers section ────────────
    src = apply(
        src,
        old="# ============================================================================\n# Error Handlers\n# ============================================================================",
        new=(
            "# ============================================================================\n"
            "# Stock Trading Routes — JSE + US + BTC Correlation\n"
            "# ============================================================================\n"
            "\n"
            "@app.route('/api/stocks/jse', methods=['GET'])\n"
            "def get_jse_overview():\n"
            "    \"\"\"Get JSE Top 50 price overview\"\"\"\n"
            "    try:\n"
            "        if not stock_market:\n"
            "            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503\n"
            "        top_n = int(request.args.get('top_n', config.JSE_TOP_N if hasattr(config, 'JSE_TOP_N') else 20))\n"
            "        overview = stock_market.get_jse_overview(top_n=top_n)\n"
            "        return jsonify({\n"
            "            'success': True,\n"
            "            'count': len(overview),\n"
            "            'stocks': overview,\n"
            "            'market': 'JSE',\n"
            "            'currency': 'ZAR',\n"
            "            'timestamp': datetime.now().isoformat()\n"
            "        })\n"
            "    except Exception as e:\n"
            "        logger.error(f'Error fetching JSE overview: {e}')\n"
            "        return jsonify({'success': False, 'error': str(e)}), 500\n"
            "\n"
            "\n"
            "@app.route('/api/stocks/us', methods=['GET'])\n"
            "def get_us_overview():\n"
            "    \"\"\"Get US Top stocks price overview\"\"\"\n"
            "    try:\n"
            "        if not stock_market:\n"
            "            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503\n"
            "        overview = stock_market.get_us_overview()\n"
            "        return jsonify({\n"
            "            'success': True,\n"
            "            'count': len(overview),\n"
            "            'stocks': overview,\n"
            "            'market': 'US',\n"
            "            'currency': 'USD',\n"
            "            'timestamp': datetime.now().isoformat()\n"
            "        })\n"
            "    except Exception as e:\n"
            "        logger.error(f'Error fetching US stocks overview: {e}')\n"
            "        return jsonify({'success': False, 'error': str(e)}), 500\n"
            "\n"
            "\n"
            "@app.route('/api/stocks/btc-signal', methods=['GET'])\n"
            "def get_btc_correlation_signal():\n"
            "    \"\"\"\n"
            "    BTC Correlation Signal — compares JSE Top 50 vs BTC 30-day performance.\n"
            "    Returns a crypto positioning recommendation based on relative strength.\n"
            "\n"
            "    Query params:\n"
            "      use_jse=true/false   (default: true)\n"
            "      use_us=true/false    (default: false)\n"
            "      top_n=20             (number of JSE stocks to include)\n"
            "    \"\"\"\n"
            "    try:\n"
            "        if not stock_market:\n"
            "            return jsonify({'success': False, 'error': 'StockMarketClient not available — install yfinance'}), 503\n"
            "\n"
            "        use_jse = request.args.get('use_jse', 'true').lower() == 'true'\n"
            "        use_us  = request.args.get('use_us', 'false').lower() == 'true'\n"
            "        top_n   = int(request.args.get('top_n', 20))\n"
            "\n"
            "        # Get BTC 30d return from FreeMarketClient if available\n"
            "        btc_return_30d = None\n"
            "        if free_market:\n"
            "            try:\n"
            "                btc_returns = stock_market.get_30d_returns(['BTC-USD'])\n"
            "                btc_return_30d = btc_returns.get('BTC-USD')\n"
            "            except Exception:\n"
            "                pass\n"
            "\n"
            "        signal = stock_market.btc_correlation_signal(\n"
            "            btc_return_30d=btc_return_30d,\n"
            "            use_jse=use_jse,\n"
            "            use_us=use_us,\n"
            "            top_n=top_n,\n"
            "        )\n"
            "\n"
            "        return jsonify({\n"
            "            'success':            True,\n"
            "            'crypto_signal':      signal.crypto_signal,\n"
            "            'confidence':         signal.confidence,\n"
            "            'btc_return_30d':     signal.btc_return_30d,\n"
            "            'stock_return_30d':   signal.stock_return_30d,\n"
            "            'relative_strength':  signal.relative_strength,\n"
            "            'top_performers':     signal.top_performers[:10],\n"
            "            'underperformers':    signal.underperformers[:10],\n"
            "            'reasoning':          signal.reasoning,\n"
            "            'basket':             'JSE Top 50' if use_jse else 'US Stocks',\n"
            "            'timestamp':          datetime.now().isoformat()\n"
            "        })\n"
            "    except Exception as e:\n"
            "        logger.error(f'Error computing BTC correlation signal: {e}')\n"
            "        return jsonify({'success': False, 'error': str(e)}), 500\n"
            "\n"
            "\n"
            "@app.route('/api/stocks/alpaca', methods=['GET'])\n"
            "def get_alpaca_status():\n"
            "    \"\"\"Get Alpaca account status and open positions\"\"\"\n"
            "    try:\n"
            "        if not alpaca_client or not alpaca_client.is_ready:\n"
            "            return jsonify({\n"
            "                'success': False,\n"
            "                'error': 'AlpacaClient not configured — set ALPACA_API_KEY + ALPACA_API_SECRET in .env',\n"
            "                'setup_url': 'https://alpaca.markets'\n"
            "            }), 503\n"
            "\n"
            "        account   = alpaca_client.get_account()\n"
            "        positions = alpaca_client.get_positions()\n"
            "        market_open = alpaca_client.is_market_open()\n"
            "\n"
            "        return jsonify({\n"
            "            'success':      True,\n"
            "            'account':      account,\n"
            "            'positions':    positions,\n"
            "            'market_open':  market_open,\n"
            "            'mode':         'LIVE' if alpaca_client.is_live else 'PAPER',\n"
            "            'timestamp':    datetime.now().isoformat()\n"
            "        })\n"
            "    except Exception as e:\n"
            "        logger.error(f'Error fetching Alpaca status: {e}')\n"
            "        return jsonify({'success': False, 'error': str(e)}), 500\n"
            "\n"
            "\n"
            "@app.route('/api/stocks/sepolia-pairs', methods=['GET'])\n"
            "def get_sepolia_pairs():\n"
            "    \"\"\"List available Sepolia testnet token pairs for on-chain submission\"\"\"\n"
            "    pairs = getattr(config, 'SEPOLIA_TEST_PAIRS', ['WBTC/USDC'])\n"
            "    primary = getattr(config, 'SEPOLIA_PRIMARY_PAIR', 'WBTC/USDC')\n"
            "    return jsonify({\n"
            "        'success':      True,\n"
            "        'pairs':        pairs,\n"
            "        'primary_pair': primary,\n"
            "        'network':      'Sepolia Testnet',\n"
            "        'chain_id':     config.CHAIN_ID,\n"
            "        'note':         'Get test ETH at https://sepoliafaucet.com, test LINK at https://faucets.chain.link',\n"
            "        'timestamp':    datetime.now().isoformat()\n"
            "    })\n"
            "\n"
            "\n"
            "# ============================================================================\n"
            "# Error Handlers\n"
            "# ============================================================================"
        ),
        label="dashboard_server — add /api/stocks/* routes",
    )

    # ── 2d: Update /api/health to include stock client status ─────────────────
    src = apply(
        src,
        old=(
            "    return jsonify({\n"
            "        'status': 'healthy',\n"
            "        'timestamp': datetime.now().isoformat(),\n"
            "        'prism_connected': prism_client is not None,\n"
            "        'free_market_connected': free_market is not None,\n"
            "    })"
        ),
        new=(
            "    return jsonify({\n"
            "        'status':                'healthy',\n"
            "        'timestamp':             datetime.now().isoformat(),\n"
            "        'prism_connected':       prism_client is not None,\n"
            "        'free_market_connected': free_market is not None,\n"
            "        'stock_market_ready':    stock_market is not None,\n"
            "        'alpaca_ready':          alpaca_client is not None and alpaca_client.is_ready,\n"
            "        'alpaca_mode':           ('LIVE' if alpaca_client and alpaca_client.is_live else 'PAPER') if alpaca_client else 'N/A',\n"
            "        'jse_enabled':           getattr(config, 'JSE_ENABLED', False),\n"
            "        'us_stocks_enabled':     getattr(config, 'US_STOCKS_ENABLED', False),\n"
            "        'btc_correlation':       getattr(config, 'BTC_CORRELATION_ENABLED', False),\n"
            "        'sepolia_pairs':         len(getattr(config, 'SEPOLIA_TEST_PAIRS', [])),\n"
            "    })"
        ),
        label="dashboard_server — update /api/health with stock status",
    )

    # ── 2e: Update startup log to show new endpoints ──────────────────────────
    src = apply(
        src,
        old='    logger.info("   - GET  /office               → Pixel office display")',
        new=(
            '    logger.info("   - GET  /office               → Pixel office display")\n'
            '    logger.info("   - GET  /api/stocks/jse       → JSE Top 50 overview")\n'
            '    logger.info("   - GET  /api/stocks/us        → US Top stocks overview")\n'
            '    logger.info("   - GET  /api/stocks/btc-signal → JSE vs BTC correlation signal")\n'
            '    logger.info("   - GET  /api/stocks/alpaca    → Alpaca account + positions")\n'
            '    logger.info("   - GET  /api/stocks/sepolia-pairs → Sepolia testnet token pairs")'
        ),
        label="dashboard_server — add stock routes to startup log",
    )

    save(DASHBOARD, src)
    print(f"  ✅ {DASHBOARD} saved\n")


# ── Installation reminder ─────────────────────────────────────────────────────

print("=" * 60)
print("✅ Stock integration patch complete.\n")
print("Next steps:")
print()
print("1. Install dependencies:")
print("   pip install yfinance --break-system-packages")
print("   pip install alpaca-py --break-system-packages")
print()
print("2. Copy new files to your project:")
print("   cp ~/Downloads/stock_market.py  data/stock_market.py")
print("   cp ~/Downloads/alpaca_client.py execution/alpaca_client.py")
print()
print("3. Add Alpaca keys to your .env:")
print("   ALPACA_API_KEY=your_key_here")
print("   ALPACA_API_SECRET=your_secret_here")
print("   ALPACA_LIVE=false  # keep false for paper trading")
print()
print("4. Get free Alpaca paper keys at: https://alpaca.markets")
print()
print("5. Restart the server:")
print("   python3 dashboard_server.py")
print()
print("New API endpoints:")
print("   GET /api/stocks/jse           → JSE Top 50 prices (ZAR)")
print("   GET /api/stocks/us            → US Top 20 prices (USD)")
print("   GET /api/stocks/btc-signal    → JSE vs BTC correlation signal")
print("   GET /api/stocks/alpaca        → Alpaca paper account + positions")
print("   GET /api/stocks/sepolia-pairs → Testnet token pairs")
print("=" * 60)
