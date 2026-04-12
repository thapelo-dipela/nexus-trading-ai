"""
NEXUS Configuration — all env vars, defaults, and constants.
"""
import os
from dotenv import load_dotenv
load_dotenv()

# PRISM Configuration
PRISM_API_KEY = os.getenv("PRISM_API_KEY", "prism_sk_C8ZTr-AEX6IkDGfLmdm7RXa5ZOIG29H5xc57pUCPGRQ")
PRISM_API_BASE_URL = "https://api.prismapi.ai"
PRISM_SYMBOL = os.getenv("PRISM_SYMBOL", "BTC")
PRISM_OHLCV_INTERVAL = int(os.getenv("PRISM_OHLCV_INTERVAL", "60"))  # minutes

# PRISM Cache TTLs (seconds)
PRISM_CACHE_TTL_RESOLVE = 3600  # 1 hour
PRISM_CACHE_TTL_PRICE = 15  # 15 seconds
PRISM_CACHE_TTL_SIGNALS = 180  # 3 minutes (increased from 2m to reduce API calls)
PRISM_CACHE_TTL_RISK = 300  # 5 minutes

# PRISM Risk Thresholds
PRISM_RISK_VETO_THRESHOLD = float(os.getenv("PRISM_RISK_VETO_THRESHOLD", "95"))

# Kraken Configuration
KRAKEN_CLI_PATH = os.getenv("KRAKEN_CLI_PATH", "kraken")
PAIR = os.getenv("NEXUS_PAIR", "XXBTZUSD")

# Kraken API (read-only for lablab.ai competition leaderboard)
KRAKEN_API_KEY = os.getenv("KRAKEN_API_KEY", "VuE3f6deQM43x2OjspNexrLiS069Z8Fm+IHuB1NyQwiJZiPamlTv6li+")
KRAKEN_API_SECRET = os.getenv("KRAKEN_API_SECRET", "KzDQWwjYJuHFmW8BMIJgn0UnS32pBJhDsLTsmrgDQysdiXvrSB/DjADfb4VwMV3uos56LOR/VWwkxFs4lT7HpA==")
KRAKEN_SUBMISSION_ENABLED = os.getenv("KRAKEN_SUBMISSION_ENABLED", "true").lower() == "true"

# Loop Configuration
LOOP_INTERVAL_SECONDS = int(os.getenv("NEXUS_LOOP_INTERVAL", "300"))

# Risk Limits
MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", "5.0"))
MAX_POSITION_PCT = float(os.getenv("MAX_POSITION_PCT", "20.0"))
VOLATILITY_THRESHOLD = float(os.getenv("VOLATILITY_THRESHOLD", "0.07"))

# Position Sizing
RISK_PCT_PER_TRADE = float(os.getenv("RISK_PCT_PER_TRADE", "0.01"))
MIN_TRADE_SIZE_USD = float(os.getenv("MIN_TRADE_SIZE_USD", "10.0"))
MAX_TRADE_SIZE_USD = float(os.getenv("MAX_TRADE_SIZE_USD", "500.0"))

# Risk-Adjusted Returns & Compliance (Hackathon Standards)
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "3.0"))
MIN_VOLUME_24H_USD = float(os.getenv("MIN_VOLUME_24H_USD", "1e9"))  # 1B minimum
MAX_SLIPPAGE_PCT = float(os.getenv("MAX_SLIPPAGE_PCT", "0.5"))
MIN_SHARPE_RATIO = float(os.getenv("MIN_SHARPE_RATIO", "0.5"))
TARGET_VOLATILITY_PCT = float(os.getenv("TARGET_VOLATILITY_PCT", "10.0"))

# Consensus Configuration
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.20"))
INITIAL_AGENT_WEIGHT = 1.0
WEIGHT_LEARN_RATE = 0.1
AGENT_RETIREMENT_FLOOR_TRADES = 10  # consecutive trades at floor before retirement
ROLLING_ACCURACY_WINDOW = 20  # trades

# On-chain Configuration (ERC-8004 Ethereum Sepolia)
RPC_URL = os.getenv("RPC_URL", "https://rpc.sepolia.org")
AGENT_WALLET_KEY = os.getenv("AGENT_WALLET_KEY", "")

# ✅ REQUIRED: These are the official shared contracts - DO NOT CHANGE
AGENT_REGISTRY_ADDRESS = os.getenv("AGENT_REGISTRY_ADDRESS", "0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3")
HACKATHON_VAULT_ADDRESS = os.getenv("HACKATHON_VAULT_ADDRESS", "0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90")
RISK_ROUTER_ADDRESS = os.getenv("RISK_ROUTER_ADDRESS", "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC")
REPUTATION_REGISTRY_ADDRESS = os.getenv("REPUTATION_REGISTRY_ADDRESS", "0x423a9904e39537a9997fbaF0f220d79D7d545763")
VALIDATION_REGISTRY_ADDRESS = os.getenv("VALIDATION_REGISTRY_ADDRESS", "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1")

# Sentiment Configuration — Free, no-signup multi-source APIs
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1"
COINGECKO_TRENDING = "https://api.coingecko.com/api/v3/search/trending"
COINGECKO_COMMUNITY = "https://api.coingecko.com/api/v3/coins/bitcoin"
MESSARI_METRICS = "https://data.messari.io/api/v1/assets/btc/metrics"

# Position Management (exit conditions)
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "5.0"))  # close if up 5%
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "2.0"))  # close if down 2%
MAX_HOLD_TIME_MINUTES = int(os.getenv("MAX_HOLD_TIME_MINUTES", "1440"))  # 24 hours

# Persistence Files
WEIGHTS_FILE = "nexus_weights.json"
HOLD_LOG_FILE = "hold_log.json"
POSITIONS_FILE = "nexus_positions.json"
EQUITY_CURVE_FILE = "nexus_equity_curve.json"
CYCLE_LOG_FILE = "nexus_cycle_log.json"

# LLM Reasoner Configuration (Task B) — UPDATED FOR GROQ + OPENCLAW
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")  # DEPRECATED, kept for compatibility
LLM_REASONER_TIMEOUT = int(os.getenv("LLM_REASONER_TIMEOUT", "15"))
LLM_REASONER_WEIGHT = float(os.getenv("LLM_REASONER_WEIGHT", "2.0"))  # 6th highest voting weight

# OpenClaw Configuration (Quantum Board of Directors)
OPENCLAW_ENABLED = os.getenv("OPENCLAW_ENABLED", "true").lower() == "true"
OPENCLAW_MODEL = "llama-3.3-70b-versatile"  # Groq-hosted model

# Board Director Weights (for dynamic voting)
BOARD_DIRECTOR_WEIGHTS = {
    "alpha": 1.2,    # Technical analysis (slightly elevated)
    "beta": 1.1,     # Sentiment analysis
    "gamma": 1.4,    # Risk officer (elevated for safety)
    "delta": 1.0,    # Flow/rotation signals
}

# Leverage Rules (Board Consensus → Position Leverage)
BOARD_LEVERAGE_UNANIMOUS = 4.0      # 4/4 directors agree
BOARD_LEVERAGE_MAJORITY = 2.5       # 3/4 directors agree
BOARD_LEVERAGE_SPLIT = 1.5          # 2/4 directors agree (low conviction)
BOARD_LEVERAGE_CONFLICT = 1.0       # HOLD or no position

# Exit Target Rules (Profit-Taking)
BOARD_EXIT_STANDARD_PCT = 25.0      # Standard: Director Gamma's rule
BOARD_EXIT_RISKOFF_PCT = 50.0       # High-risk extension (if leverage active + sentiment strong)

# Reddit/News Sentiment Thresholds
SENTIMENT_THRESHOLD_BULLISH = 70.0  # % positive
SENTIMENT_THRESHOLD_BEARISH = 30.0  # % positive
SENTIMENT_VOLUME_THRESHOLD = 100    # Minimum Reddit mentions to trigger signals

# Web Scraping Configuration (Reddit + News Sentiment)
REDDIT_SUBREDDITS = ["CryptoCurrency", "WallStreetBets", "bitcoin", "ethereum"]
REDDIT_KEYWORDS = ["moon", "rug", "squeeze", "mainnet", "launch", "ai", "layer2", "rwa", "dump", "hodl"]
NEWS_SENTIMENT_KEYWORDS_BULLISH = ["bullish", "surge", "launch", "milestone", "partnership", "upgrade"]
NEWS_SENTIMENT_KEYWORDS_BEARISH = ["bearish", "crash", "risk", "hack", "collapse", "warning"]

# Sentiment API Configuration (Optional)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY", "")  # For news sentiment extraction
REDDIT_API_ID = os.getenv("REDDIT_API_ID", "")
REDDIT_API_SECRET = os.getenv("REDDIT_API_SECRET", "")

# Order Flow Configuration (Task A)
CVD_LOOKBACK_BARS = int(os.getenv("CVD_LOOKBACK_BARS", "30"))
CVD_VETO_THRESHOLD = float(os.getenv("CVD_VETO_THRESHOLD", "0.15"))
VWAP_DIVERGENCE_PCT = float(os.getenv("VWAP_DIVERGENCE_PCT", "1.0"))

# Sentiment Multi-Source Configuration (Task D)
CRYPTOPANIC_URL = "https://cryptopanic.com/api/v1/posts/?currencies=BTC&kind=news&public=true"
# COINGECKO_COMMUNITY already defined above (reuse for social_score)

# Hard Limits (ERC-8004 Hackathon)
MAX_TRADES_PER_HOUR = int(os.getenv("MAX_TRADES_PER_HOUR", "10"))
CHAIN_ID = 11155111  # Sepolia testnet — NEVER CHANGE

# Strategy Registry (Section 6E - 10 Strategies)
AVAILABLE_STRATEGIES = [
    "trend_following",     # 50/200 EMA crossover
    "breakout",            # support/resistance + volume
    "mean_reversion",      # RSI + Bollinger, ranging
    "scalping",            # sub-5min, tight TP/SL
    "swing",               # multi-day holds
    "algorithmic_quant",   # NEXUS default, balanced
    "arbitrage",           # cross-exchange price diffs
    "smc",                 # Smart Money Concepts
    "position",            # macro trend, weeks-months
    "yolo",                # extreme bullish, max aggression
]
ACTIVE_STRATEGY = os.getenv("ACTIVE_STRATEGY", "algorithmic_quant")

# YOLO Agent Configuration (Section 6F)
YOLO_ENABLED = os.getenv("YOLO_ENABLED", "false").lower() == "true"
YOLO_MAX_ACTIVATIONS_24H = 3
YOLO_COOLDOWN_AFTER_SL = 3600  # 1 hour in seconds
YOLO_FEAR_GREED_MIN = 75
YOLO_CVD_MOMENTUM_MIN = 0.20
YOLO_PRISM_RISK_MAX = 60
YOLO_DRAWDOWN_MAX_PCT = 3.0

# Etherscan API (for audit trail links - Sepolia)
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")

