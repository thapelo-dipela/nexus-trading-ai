# NEXUS — Master Build Index

Complete implementation of the NEXUS self-improving multi-agent trading system.

## 📖 Documentation (Read in Order)

1. **SYSTEM_SUMMARY.md** ← **START HERE** — Complete overview with quick start guide
2. **README.md** — Full user documentation (setup, usage, troubleshooting)
3. **BUILD_SUMMARY.md** — Component-by-component implementation details
4. **IMPLEMENTATION_CHECKLIST.md** — Verification checklist and deployment readiness

## 🗂️ File Structure

```
nexus/
├── main.py                           # Entry point with CLI (--ping, --dry-run, --leaderboard)
├── config.py                         # Configuration + env vars with defaults
├── requirements.txt                  # Python dependencies
├── .env.example                      # Configuration template
│
├── agents/
│   ├── __init__.py                   # Factory: create_default_agents()
│   ├── base.py                       # Dataclasses: MarketData, Vote, TradeDecision
│   ├── momentum.py                   # Momentum agent (TA + PRISM signals)
│   ├── sentiment.py                  # Sentiment agent (contrarian + Fear/Greed)
│   └── risk_guardian.py              # Risk agent (4 veto conditions)
│
├── consensus/
│   ├── __init__.py                   # Exports
│   └── engine.py                     # Voting + PnL-proportional learning
│
├── data/
│   ├── __init__.py                   # MarketDataBuilder
│   └── prism.py                      # PRISM API client with caching
│
├── execution/
│   ├── __init__.py                   # Position sizing
│   └── kraken.py                     # Kraken execution (no data fetching)
│
├── onchain/
│   ├── __init__.py                   # Exports
│   └── reputation.py                 # EIP-712 signing + Web3
│
└── Documentation/
    ├── SYSTEM_SUMMARY.md             # Quick start + overview
    ├── README.md                     # Complete user guide
    ├── BUILD_SUMMARY.md              # Implementation details
    ├── IMPLEMENTATION_CHECKLIST.md   # Verification checklist
    └── this file (INDEX.md)
```

## 🚀 Quick Start

### Installation
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### Verify Connectivity
```bash
python main.py --ping
```

### Dry Run (Simulation)
```bash
python main.py --dry-run
```

### Live Trading
```bash
python main.py
```

### Monitor Agents
```bash
python main.py --leaderboard
```

## 🎯 Core Concepts

### PRISM Data Backbone
- **API endpoints**: resolve, price, signals (1h+4h), risk
- **TTL caching**: 1h, 15s, 2min, 5min respectively
- **Graceful fallback**: All failures result in safe defaults
- **No exceptions**: All PRISM calls wrapped in try/except

### Three Specialized Agents
1. **MomentumAgent** — Local TA (RSI, MACD, BB) blended with PRISM signals
2. **SentimentAgent** — Contrarian positioning from Fear/Greed and news NLP
3. **RiskGuardianAgent** — Hard veto triggers (risk score, drawdown, ATR, position %)

### Reputation-Weighted Consensus
- Votes weighted by agent reputation (0.1–5.0)
- Consensus = weighted average buy/sell scores
- Threshold: 0.55 confidence before executing trade
- Learning: PnL-proportional weight updates with tanh scaling
- Dissenter credit: Rewards agents who correctly disagree
- Retirement: Agents at floor weight for 10 trades auto-retire

### Position Sizing
- Base: 1% of portfolio equity
- Volatility scalar: reduces size when ATR high
- Confidence scalar: scales with consensus confidence
- Clamped to [10, 500] USD by default

### On-Chain Verification
- EIP-712 signed trade outcomes
- Base Sepolia integration (chainId 84532)
- Recoverable signer for verification
- Audit trail for all trades

## ⚙️ Configuration

All config via environment variables in `.env`:

```
PRISM_API_KEY=prism_sk_...              # Required
KRAKEN_CLI_PATH=/path/to/kraken        # Required
NEXUS_PAIR=XBTUSD                       # Required
PRISM_SYMBOL=BTC                        # Required

NEXUS_LOOP_INTERVAL=300                 # Loop interval (seconds)
CONFIDENCE_THRESHOLD=0.55               # Min confidence to trade
MAX_DRAWDOWN_PCT=5.0                    # Drawdown veto threshold
VOLATILITY_THRESHOLD=0.04               # ATR veto threshold
PRISM_RISK_VETO_THRESHOLD=75            # Risk score veto

RISK_PCT_PER_TRADE=0.01                 # 1% equity risk
MIN_TRADE_SIZE_USD=10.0                 # Minimum position
MAX_TRADE_SIZE_USD=500.0                # Maximum position

RPC_URL=https://sepolia.base.org        # On-chain
AGENT_WALLET_KEY=0x...                  # Private key for signing
REPUTATION_REGISTRY_ADDRESS=0x...       # Contract address
```

## 📊 Logging

| Format | Level | Usage |
|--------|-------|-------|
| `[bold green]` | INFO | Profitable trades, successful operations |
| `[bold red]` | ERROR | Losses, critical failures |
| `[dim]` | DEBUG | Component scores, DRY-RUN intents |
| `[yellow]` | WARNING | Vetoes, retired agents, API issues |
| `[red]` | ERROR | PRISM failures, execution problems |

## 💾 Persistence

**nexus_weights.json** — Agent reputation persisted after each trade:

```json
[
  {
    "agent_id": "momentum",
    "weight": 1.2,
    "trades_closed": 42,
    "pnl_total": 123.45,
    "wins": 28,
    "losses": 14,
    "retired": false
  }
]
```

Loaded on startup for cross-session learning.

## 🔒 Security Notes

- Never commit `.env` to version control
- Private key stored only in `.env` and memory
- All signatures are EIP-712 compliant
- On-chain audit trail for verification
- No logging of sensitive data

## 📈 System Flow (One Trade Cycle)

1. **Fetch MarketData** ← PRISM (price, candles, signals, risk) + sentiment + Kraken (portfolio)
2. **Agent Analysis** ← Each agent analyzes and votes
3. **Consensus** ← Reputation-weighted voting
4. **Risk Check** ← RiskGuardianAgent veto conditions
5. **Position Size** ← Volatility-scaled, confidence-scaled
6. **Execute** ← market_buy or market_sell via Kraken
7. **Record** ← Save trade outcome, update weights
8. **Sign** ← EIP-712 signature for on-chain verification
9. **Persist** ← Save nexus_weights.json

Repeat every 5 minutes (configurable).

## 🛠️ Development

### Type Checking
```bash
mypy main.py agents/ consensus/ data/ execution/ onchain/
```

### Running Tests
```bash
# Dry-run for 24 hours
python main.py --dry-run

# Check leaderboard
python main.py --leaderboard
```

### Debugging
```bash
python main.py -v  # Verbose (DEBUG) logging
```

## 📋 Specification Compliance

✅ All requirements from master directive implemented:
- PRISM API integration with all endpoints
- Per-endpoint TTL caching
- Graceful fallback behavior
- Kraken CLI execution-only
- Three specialized agents
- Reputation-weighted consensus
- PnL-proportional learning
- Dissenter credit mechanism
- Rolling accuracy window
- Agent retirement logic
- Counterfactual HOLD logging
- Volatility-scaled position sizing
- EIP-712 signing
- On-chain reputation registry
- Dry-run mode
- Rich CLI with --ping, --leaderboard, --dry-run
- Weight persistence
- Full type hints
- Comprehensive error handling
- Production-ready logging

## 🎓 Next Steps

1. Read **SYSTEM_SUMMARY.md** for overview
2. Copy `.env.example` to `.env` and configure
3. Run `python main.py --ping` to verify connectivity
4. Run `python main.py --dry-run` for 24+ hours
5. Monitor with `python main.py --leaderboard`
6. Deploy on-chain smart contracts
7. Run `python main.py` for live trading

## 📞 Support

- Refer to **README.md** for troubleshooting
- Check **IMPLEMENTATION_CHECKLIST.md** for verification
- See **BUILD_SUMMARY.md** for component details

---

**Status**: 🟢 **COMPLETE AND READY FOR DEPLOYMENT**

*NEXUS — Neural Exchange Unified Strategy*  
*Self-Improving Multi-Agent Trading System (2026)*
