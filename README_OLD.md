# NEXUS — Self-Improving Multi-Agent Trading System

NEXUS (Neural Exchange Unified Strategy) is an autonomous trading system that combines:

- **PRISM** (via api.prismapi.ai) as the canonical data backbone for market intelligence and risk metrics
- **Kraken CLI** as the sole execution layer for placing and managing live orders
- **Three specialized AI agents** that vote on every trade cycle
- **Reputation-weighted consensus engine** that learns from closed trade outcomes
- **On-chain reputation registry** (ERC-8004, Base Sepolia) that makes the learning loop verifiable

## Architecture

### System Components

```
nexus/
├── main.py                    # Orchestration loop + CLI
├── config.py                  # All config + env vars
├── agents/
│   ├── __init__.py
│   ├── base.py                # Vote, MarketData, BaseAgent dataclasses
│   ├── momentum.py            # Local TA + PRISM signal blend
│   ├── sentiment.py           # Fear/Greed + PRISM signal + news NLP
│   └── risk_guardian.py       # ATR veto + PRISM risk_score veto
├── consensus/
│   └── engine.py              # Reputation-weighted voting + PnL learning
├── data/
│   ├── __init__.py            # MarketDataBuilder — assembles snapshots
│   └── prism.py               # PRISM API client with caching
├── execution/
│   └── kraken.py              # Execution only: buy, sell, portfolio
├── onchain/
│   └── reputation.py          # EIP-712 signing + Web3 reputation push
└── contracts/
    ├── NEXUSReputationRegistry.sol
    └── NEXUSValidationRegistry.sol
```

### Critical Separation of Concerns

- **PRISM provides**: OHLCV candles, real-time price, AI signals, risk metrics
- **Kraken provides**: order execution, portfolio balance
- **No market data fetching** of any kind belongs in execution/kraken.py

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Key variables:
- `PRISM_API_KEY`: Your PRISM API key (provided)
- `KRAKEN_CLI_PATH`: Path to Kraken CLI executable
- `NEXUS_PAIR`: Trading pair (e.g., `XBTUSD`)
- `AGENT_WALLET_KEY`: Private key for on-chain reputation (Base Sepolia)

### 3. Verify Connectivity

```bash
python main.py --ping
```

This tests all four PRISM endpoints and Kraken connection before trading.

## Usage

### Live Trading

```bash
python main.py
```

Starts the live trading loop (5-minute intervals by default).

### Dry Run (Simulation)

```bash
python main.py --dry-run
```

Simulates trades without executing real orders. On-chain signatures are still generated but not pushed.

### View Agent Leaderboard

```bash
python main.py --leaderboard
```

Displays agent weights, rolling accuracy (last 20 trades), and cumulative PnL.

### Verbose Logging

```bash
python main.py -v
```

Enables DEBUG-level logging for component-level signal diagnostics.

## Agents

### MomentumAgent

Blends local technical analysis with PRISM multi-timeframe signals:

- **Local TA** (RSI-14, MACD 12/26/9, Bollinger Bands 20/2): 60% composite weight
- **PRISM 4h signal score**: 25% weight
- **PRISM 1h signal score**: 15% weight

Final composite determines direction (threshold ±0.15) and confidence.

### SentimentAgent

Contrarian sentiment analysis from multiple sources:

- **PRISM signal score** (crowded positioning proxy, faded mildly): 40% weight
- **PRISM 24h price change** (strong up = exhaustion → mild sell): 20% weight
- **Fear/Greed Index** (contrarian — extreme fear → buy): 30% weight
- **News NLP** from CryptoPanic headlines: 10% weight

### RiskGuardianAgent

Hard veto triggers (any one is sufficient to override all agents and output HOLD):

1. `prism_risk.risk_score >= PRISM_RISK_VETO_THRESHOLD` (default 75)
2. Portfolio drawdown from peak >= `MAX_DRAWDOWN_PCT` (default 5%)
3. Normalised ATR from candles >= `VOLATILITY_THRESHOLD` (default 4%)
4. Open position >= `MAX_POSITION_PCT` of portfolio (default 20%)

When not vetoing, contributes a mild signal based on PRISM risk proximity to veto threshold.

## PRISM API Integration

### Endpoints Used

All PRISM calls are wrapped in try/except with graceful fallbacks.

| Endpoint | TTL | Purpose |
|----------|-----|---------|
| `GET /resolve/{asset}` | 1h | Resolve ticker to canonical PRISM ID |
| `GET /crypto/{symbol}/price` | 15s | Real-time price + 24h metrics |
| `GET /signals/{symbol}` | 2min | AI signal (direction, confidence, score) |
| `GET /risk/{symbol}` | 5min | Volatility and risk metrics |

### Caching Strategy

Per-endpoint TTL caching ensures we stay within the ~15,000 free credit budget.

### Fallback Behavior

If PRISM is unavailable:
- Price: fallback to Kraken ticker
- Signals: neutral (HOLD, 0 confidence)
- Risk: risk_score = 50 (medium risk)

## Consensus Engine

### Weight Updates (PnL-Proportional Learning)

Weights are boosted or penalised based on trade outcomes:

```python
magnitude = tanh(abs(pnl_usd) / TRADE_SIZE_USD)  # 0–1
delta = WEIGHT_LEARN_RATE * confidence * magnitude
weight = clamp(weight ± delta, 0.1, 5.0)
```

### Dissenter Credit

When a trade closes as a loss, agents whose vote differed from consensus receive mild positive credit:

```python
boost(agent, 0.3 * confidence, abs(pnl_usd))
```

This rewards agents that correctly dissented.

### Rolling Accuracy Window

Each agent maintains a deque of the last 20 trade outcomes (1=correct, 0=incorrect). The displayed accuracy in `--leaderboard` uses this window. Weights still update via cumulative rule.

### Agent Retirement

If an agent's weight has been at or below 0.15 for 10 consecutive trades, it is marked `retired=True`. Retired agents are excluded from voting but still receive market data. The operator can inspect the leaderboard and decide whether to intervene.

### Counterfactual HOLD Logging

When consensus outputs HOLD, a timestamp and prices are recorded. After 12 cycles (~1 hour), the system checks what PnL would have resulted and logs:

```
[dim]Counterfactual HOLD: would have been +$X.XX if {direction}[/dim]
```

No weights are updated from counterfactuals — log only.

## Position Sizing

Risk 1% of portfolio equity per trade, scaled by confidence and volatility:

```python
base_risk = portfolio_value * 0.01
vol_scalar = max(0.3, 1.0 - (atr_pct / VOLATILITY_THRESHOLD))
sized = base_risk * confidence * vol_scalar
```

Position size is clamped to `[MIN_TRADE_SIZE_USD, MAX_TRADE_SIZE_USD]`.

## On-Chain Reputation

After every closed trade, the system signs and pushes the outcome to the NEXUSReputationRegistry (Base Sepolia):

### EIP-712 Signing

Trade outcomes are signed with EIP-712, creating a verifiable record of:
- Trade direction (BUY/SELL)
- Consensus confidence
- Profit/loss in USD
- Agent votes and their weights

### On-Chain Verification

External verifiers (judges, auditors) can:
1. Recover the signer's address from the signature
2. Verify it matches the registered NEXUS agent wallet
3. Confirm the trade logic via the contract code

This makes the learning loop completely transparent and auditable.

## Configuration

All config lives in `config.py` with environment variable overrides:

```python
PRISM_API_KEY = os.getenv("PRISM_API_KEY", "")
LOOP_INTERVAL_SECONDS = int(os.getenv("NEXUS_LOOP_INTERVAL", "300"))
MAX_DRAWDOWN_PCT = float(os.getenv("MAX_DRAWDOWN_PCT", "5.0"))
# ... etc
```

See `.env.example` for all available configuration options.

## Logging

Rich console logging conventions:

- `[bold green]`: Profitable closes
- `[bold red]`: Losses
- `[dim]`: Signal details and component scores
- `[yellow]`: Warnings (vetoes, connection issues, agent retirement)
- `[red]`: Errors (PRISM failures, execution issues)

## Weight Persistence

Agent weights are persisted to `nexus_weights.json` after every trade outcome:

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

On startup, weights are loaded from this file, allowing agents to retain their learned reputation across sessions.

## Dry-Run Mode

In dry-run mode (`--dry-run`):
- No real orders are placed on Kraken
- PRISM data is still fetched (no-op for simulation)
- Trade intents are logged at [dim] level
- On-chain signatures are generated but not broadcast
- This is useful for backtesting and validation

## Troubleshooting

### PRISM Unavailable

Check that:
1. `PRISM_API_KEY` is set in `.env`
2. Network connectivity to `api.prismapi.ai` is available
3. The API key has not exceeded daily credit limits

The system will continue with fallback values (neutral signals, risk_score=50).

### Kraken Connection Issues

Check that:
1. `KRAKEN_CLI_PATH` points to the correct Kraken CLI executable
2. Kraken CLI is configured with valid API credentials
3. Network connectivity to Kraken is available

### Low Agent Weights

If agents are being retired (weight ≤ 0.15 for 10 trades):
- Check that agents are not systematically wrong for the current market regime
- Inspect `--leaderboard` to see which agents are retiring and why
- Consider adjusting PRISM signal weights or local TA parameters

## Coding Standards

- All agents inherit `BaseAgent` and return a `Vote` from `analyze()`
- All weight mutations go through `_boost()` and `_penalise()` in `ConsensusEngine`
- Full Python type hints on every function and dataclass field
- Every PRISM call wrapped in try/except with fallback
- No unhandled PRISM exceptions allowed
- Rich console logging with proper severity levels

## Security Notes

### Private Key Management

The `AGENT_WALLET_KEY` is used for EIP-712 signing. Ensure:
- Never commit `.env` to version control
- Use `.env.example` as a template
- Rotate keys periodically
- Use hardware wallets for production deployments

### On-Chain Auditing

All trades are signed and recorded on-chain, creating an immutable audit trail. Anyone with the contract address can verify:
- The authenticity of each trade decision
- The agent's reputation at the time
- The exact consensus weights and votes

## Future Enhancements

- [ ] Multi-asset trading (currently BTC/XBTUSD only)
- [ ] Advanced TA indicators (volume profile, order flow, etc.)
- [ ] ML-based signal generation
- [ ] Dynamic timeframe selection
- [ ] Slippage protection and partial fills
- [ ] Real-time Discord/Slack notifications
- [ ] Web dashboard with live metrics

## License

Proprietary — NEXUS Trading System (2026)

## Support

For issues or questions, refer to:
- `SETUP.md` for detailed setup instructions
- Smart contract documentation in `contracts/`
- PRISM API docs at https://api.prismapi.ai/docs
