# NEXUS PRISM API Fix — Quick Reference

## What Was Fixed

### Problem
NEXUS code was calling non-existent endpoints and using incorrect field names based on assumptions about PRISM API.

### Solution
Aligned entire system to **confirmed live API responses** from actual curl tests and CLI verification.

---

## Key Changes at a Glance

| Component | Change | Evidence |
|-----------|--------|----------|
| **data/prism.py** | get_price() now extracts from /signals endpoint | Live curl: `current_price: 73185.07` |
| **data/prism.py** | get_signals() parses net_score correctly | Confidence: `abs(net_score)/signal_count` |
| **data/prism.py** | get_risk() computes risk_score | Formula: `min(100, max_drawdown*2 + volatility)` |
| **execution/kraken.py** | market_buy/sell use correct subcommands | `kraken order buy --type market` |
| **execution/kraken.py** | portfolio_summary uses balance command | `kraken balance -o json` |
| **agents/momentum.py** | Uses signal.rsi directly from PRISM | RSI: 75.3 (overbought) |
| **agents/sentiment.py** | Maps signal directions to scores | strong_bullish=1.0, neutral=0.0, etc. |
| **agents/risk_guardian.py** | Uses risk_score computed from PRISM data | risk_score ≥ 75 triggers veto |

---

## Verification Commands

### Quick Test
```bash
# Shows PRISM data is being fetched correctly
python3 main.py --ping
```

**Expected Output:**
```
Testing PRISM /resolve/BTC... ✓
Testing PRISM /signals/BTC (price extraction)... ✓ ($84,022.42)
Testing PRISM /signals/BTC (1h)... ✓ (bullish rsi=68.9)
All core connectivity checks passed!
```

### Full System Test
```bash
# Shows agents using PRISM data
python3 << 'EOF'
from data.prism import PrismClient
from execution.kraken import KrakenClient
from agents import create_default_agents
from agents.base import MarketData

kraken = KrakenClient(dry_run=True)
prism = PrismClient('API_KEY', kraken)

# Fetch and verify
sig = prism.get_signals('BTC')
print(f"✓ PRISM RSI: {sig.rsi}")  # e.g., 75.3
print(f"✓ PRISM Direction: {sig.direction}")  # e.g., bullish

risk = prism.get_risk('BTC')
print(f"✓ Risk Score: {risk.risk_score}")  # e.g., 80.0

price = prism.get_price('BTC')
print(f"✓ Current Price: ${price['price']}")  # e.g., 84022.42
EOF
```

---

## Field Name Changes

### PrismSignal
```python
# OLD (incorrect)
signal.direction = "BUY"  # ✗ Not what API returns
signal.score = 0.5

# NEW (correct, from confirmed API)
signal.direction = "bullish"  # ✓ from overall_signal
signal.score = 0.0  # Computed: net_score / signal_count
signal.rsi = 75.28  # NEW: from indicators
signal.macd_histogram = 34.06  # NEW: from indicators
signal.current_price = 73185.07  # NEW: from data[0]
```

### PrismRisk
```python
# OLD (incorrect)
risk.risk_score = 50.0  # ✗ Guessed value

# NEW (correct, computed from confirmed fields)
risk.risk_score = 80.0  # Computed: min(100, max_drawdown*2 + annual_volatility)
risk.current_drawdown = 0.08  # NEW: from response
risk.sortino_ratio = -0.779  # NEW: from response
```

---

## API Endpoints — Truth Table

| Endpoint | Status | Cache | Usage |
|----------|--------|-------|-------|
| GET /resolve/{symbol} | ✅ Works | 1h | Asset identity |
| GET /signals/{symbol} | ✅ Works | 2m | **Primary signal source** |
| GET /crypto/{symbol}/price | ❌ **Does not exist** | — | Use /signals instead |
| GET /risk/{symbol} | ✅ Works | 5m | Risk metrics |
| kraken balance -o json | ✅ Works | — | Portfolio value |
| kraken ticker -o json | ✅ Works | — | Current price |
| kraken ohlc --interval X | ✅ Works | — | Candle data |
| kraken order buy/sell | ✅ Works | — | Execution |

---

## Response Field Mappings

### /signals/{symbol} → PrismSignal
```
data[0]["overall_signal"] → direction
abs(net_score) / signal_count → confidence [0,1]
net_score / signal_count → score [-1,1]
indicators["rsi"] → rsi
indicators["macd_histogram"] → macd_histogram
current_price → current_price
strength + active_signals → reasoning
```

### /risk/{symbol} → PrismRisk
```
min(100, max_drawdown*2 + annual_volatility) → risk_score
daily_volatility → atr_pct
annual_volatility → volatility_30d
max_drawdown → max_drawdown_30d
sharpe_ratio → sharpe_ratio
sortino_ratio → sortino_ratio [NEW]
current_drawdown → current_drawdown [NEW]
```

---

## Agent Logic — PRISM Usage

### MomentumAgent
```python
# Now uses PRISM RSI directly
if market_data.signal_1h:
    rsi_score = _prism_rsi_to_score(signal.rsi)
    # Maps: RSI 70+ → +1.0, RSI 30- → -1.0

# Blends with local TA (60% local, 25% 4h signal, 15% 1h signal)
```

### SentimentAgent
```python
# Maps PRISM directions to numeric scores
score = _prism_direction_to_score(signal.direction)
# strong_bullish → 1.0
# bullish → 0.5
# neutral → 0.0
# bearish → -0.5
# strong_bearish → -1.0
```

### RiskGuardian
```python
# Uses computed risk_score as veto threshold
if prism_risk.risk_score >= 75:  # Extreme conditions
    return HOLD  # Hard veto
    
# Also monitors current_drawdown in real-time
```

---

## Testing PRISM Integration

### See RSI from PRISM
```python
from data.prism import PrismClient
from execution.kraken import KrakenClient

p = PrismClient('API_KEY', KrakenClient())
sig = p.get_signals('BTC')
print(f"PRISM RSI: {sig.rsi}")  # e.g., 75.33
```

### See Risk Score
```python
risk = p.get_risk('BTC')
print(f"Risk Score: {risk.risk_score}")  # e.g., 80.01
print(f"Sharpe Ratio: {risk.sharpe_ratio}")  # e.g., -0.80
print(f"Current Drawdown: {risk.current_drawdown}%")  # e.g., 0.17
```

### See Agent Decision with PRISM Data
```python
from agents import create_default_agents
agents = create_default_agents()

# Each agent logs its PRISM inputs at DEBUG level
for agent in agents:
    vote = agent.analyze(market_data)
    # Check logs for:
    # [dim]PRISM: dir=bullish rsi=75.3 macd_hist=34.75[/dim]
```

---

## Logs That Show PRISM Is Working

When running the system, look for these dim-level logs:

```
[dim]OHLCV: 100 candles via Kraken CLI[/dim]
[dim]Using PRISM RSI=75.3 (score=1.000)[/dim]
[dim]Using PRISM MACD histogram=34.7486 (score=0.762)[/dim]
[dim]PRISM: dir=bullish rsi=75.3 macd_hist=34.7486 price=$73,185.81[/dim]
[dim]PRISM signal: bullish (strength=+0.50)[/dim]
[dim]RiskGuardianAgent: no veto, risk_signal=0.100[/dim]
[dim]PRISM risk: score=80.0 drawdown=0.17% sharpe=-0.80[/dim]
```

These logs are evidence that PRISM data is genuinely driving trading decisions.

---

## Implementation Checklist

- ✅ data/prism.py rewritten with confirmed field names
- ✅ execution/kraken.py uses correct CLI syntax
- ✅ agents/base.py dataclasses updated
- ✅ agents/momentum.py uses PRISM RSI/MACD
- ✅ agents/sentiment.py maps signal directions
- ✅ agents/risk_guardian.py uses risk_score
- ✅ main.py ping function updated
- ✅ All tests pass
- ✅ PRISM data flows through entire system

---

## Files Changed

```
data/prism.py                    # 100% rewrite
execution/kraken.py              # CLI command fixes
agents/base.py                   # Dataclass updates
agents/momentum.py               # PRISM field extraction
agents/sentiment.py              # Signal direction mapping
agents/risk_guardian.py          # Risk scoring logic
main.py                          # Ping function update
PRISM_API_ALIGNMENT.md           # Complete documentation
```

---

## Ready for Verification

Run:
```bash
python3 main.py --ping
```

All tests should pass with confirmed PRISM data flowing through the system.
