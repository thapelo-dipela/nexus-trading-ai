# NEXUS Trading - Why No Trades & No PnL

## TL;DR - Quick Fix

### You Are Likely Running in DRY-RUN Mode ❌

**Current command:**
```bash
python3 main.py
```

**This defaults to DRY-RUN!** Trades are simulated, not executed. No PnL is real.

### Solution: Use --live Flag

```bash
python3 main.py --live --verbose
```

This will:
- Execute real trades on Kraken ✅
- Record real PnL ✅
- Update equity curve with actual results ✅

---

## Why This Happens

### Root Cause: DRY-RUN Default

**File**: `main.py` line 647
```python
dry_run = args.dry_run or not args.live
```

**Logic**:
- `dry_run = True or not False` → `True or True` → **`True`** (by default)
- `dry_run = False or not True` → `False or False` → **`False`** (with `--live`)

**Implication**:
| Command | Mode | Trades | PnL |
|---------|------|--------|-----|
| `python3 main.py` | DRY-RUN | Simulated | Fake |
| `python3 main.py --dry-run` | DRY-RUN | Simulated | Fake |
| `python3 main.py --live` | **LIVE** ✅ | **Real** ✅ | **Real** ✅ |

---

## Secondary Issues (Even With --live)

If you run with `--live` but still see no trades, check these:

### Issue A: Portfolio Value Returning Zero

**Symptom**: Equity curve shows `cash: 0.0` when positions are open

**Root Cause**: `portfolio_summary()` fails and returns `(0.0, 0.0)`

**Fix**: Check Kraken CLI is working
```bash
kraken balance -o json
kraken ticker -o json XXBTZUSD
```

If these fail, Kraken CLI is not installed or not in PATH. Install via:
```bash
brew install kraken-cli  # macOS
```

### Issue B: Consensus Not Generating Buy/Sell Signals

**Symptom**: Logs show `[yellow]HOLD[/yellow]` repeatedly

**Possible Causes**:
1. **Confidence too low**: Config requires `CONFIDENCE_THRESHOLD = 0.20` (20%)
   - Agents may not agree strongly enough
   - Try lowering in config.py if testing

2. **Compliance blocking trades**:  
   - Check logs for: `[yellow]Trade blocked by compliance[/yellow]`
   - Verify Sharpe ratio, max leverage, volume requirements are met

3. **All agents voting HOLD**:
   - Check individual agent logic in `agents/` folder
   - Run with `--verbose` to see agent votes

### Issue C: Positions Open But Never Close

**Symptom**: Positions in `nexus_positions.json` have `status: "open"` forever

**Root Cause**: Stop-loss/take-profit thresholds not hit

**Check**:
```bash
cat nexus_positions.json | jq '.[] | select(.status=="open") | {entry_price, direction}'
```

Then check current price:
```bash
kraken ticker -o json XXBTZUSD | jq '.XXBTZUSD.c[0]'
```

If price hasn't moved enough, wait or lower `TAKE_PROFIT_PCT` / `STOP_LOSS_PCT` in config.

---

## What the Equity Curve Should Look Like

### Correct Pattern (With --live):
```json
[
  {
    "timestamp": 1775990000,
    "equity": 10000.0,
    "cash": 10000.0,
    "unrealised_pnl": 0.0,
    "realised_pnl": 0.0
  },
  {
    "timestamp": 1775990300,
    "equity": 10000.0,
    "cash": 9950.0,
    "unrealised_pnl": 45.0,
    "realised_pnl": 0.0
  },
  {
    "timestamp": 1775990600,
    "equity": 10045.0,
    "cash": 10000.0,
    "unrealised_pnl": 0.0,
    "realised_pnl": 45.0
  }
]
```

**Key properties**:
- ✅ Equity is **never negative**
- ✅ When position open: `cash + unrealised_pnl + realised_pnl = equity`
- ✅ Realised PnL accumulates over time
- ✅ Portfolio value fluctuates with market moves

### What You're Probably Seeing (DRY-RUN Mode):
```json
[
  {
    "timestamp": 1775990000,
    "equity": 10000.0,
    "cash": 10000.0,
    "unrealised_pnl": 0.0,
    "realised_pnl": 0.0
  },
  {
    "timestamp": 1775990300,
    "equity": -5.067490644775754,
    "cash": 0.0,
    "unrealised_pnl": 0.0,
    "realised_pnl": -5.067490644775754
  }
]
```

**Problems**:
- ❌ Equity is **negative** (impossible)
- ❌ Alternating between `equity: 10000` and `equity: -5` (flipping positions)
- ❌ Same `realised_pnl` repeated (no new trades closing)
- ❌ This indicates positions are being opened and closed in simulation only

---

## Step-by-Step: Getting Real Trades Running

### Step 1: Verify Kraken CLI Setup
```bash
# Check installation
which kraken
kraken --version

# Check connectivity
kraken balance -o json
# Expected output: {"ZUSD": "10000.0", "XXBT": "0.0312", ...}
```

### Step 2: Start NEXUS in LIVE Mode
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
python3 main.py --live --verbose
```

### Step 3: Monitor Trade Execution
**In another terminal:**
```bash
# Watch positions open/close
watch -n 5 'cat nexus_positions.json | jq ".[] | {trade_id, direction, status, entry_price}"'

# Watch equity curve
watch -n 5 'tail -3 nexus_equity_curve.json | jq ".[] | {timestamp, equity, cash, realised_pnl}"'

# Watch logs
tail -f nexus_debug.log
```

### Step 4: Verify PnL After First Trade
```bash
# After first trade closes
cat nexus_positions.json | jq '.[] | select(.status=="closed") | {trade_id, direction, pnl_usd, pnl_pct}'

# Expected output:
# {
#   "trade_id": "nexus_1775990600_buy",
#   "direction": "BUY",
#   "pnl_usd": 45.23,
#   "pnl_pct": 0.45
# }
```

---

## Configuration Tuning (If Trades Still Don't Execute)

**File**: `config.py`

### Lower the Confidence Threshold (to get more trades)
```python
CONFIDENCE_THRESHOLD = 0.20  # Current: 20%
CONFIDENCE_THRESHOLD = 0.15  # Try: 15%
```

### Adjust Stop-Loss / Take-Profit (to close positions sooner)
```python
TAKE_PROFIT_PCT = 5.0        # Current: close if +5% profit
TAKE_PROFIT_PCT = 2.0        # Try: close if +2% profit

STOP_LOSS_PCT = 2.0          # Current: close if -2% loss
STOP_LOSS_PCT = 1.0          # Try: close if -1% loss
```

### Increase Position Size (to see meaningful PnL)
```python
MIN_TRADE_SIZE_USD = 10.0     # Current: minimum $10
MIN_TRADE_SIZE_USD = 50.0     # Try: minimum $50

MAX_TRADE_SIZE_USD = 500.0    # Current: maximum $500
MAX_TRADE_SIZE_USD = 1000.0   # Try: maximum $1000
```

---

## Debugging: Enable Verbose Logging

```bash
python3 main.py --live --verbose 2>&1 | tee trading_session.log
```

Then search for key events:
```bash
# Look for trade signals
grep "BUY\|SELL" trading_session.log

# Look for compliance blocks
grep "Trade blocked" trading_session.log

# Look for Kraken errors
grep "error\|Error" trading_session.log

# Look for confidence values
grep "confidence" trading_session.log
```

---

## Checklist: Is PnL Capture Working?

- [ ] Running with `python3 main.py --live --verbose` (not just `python3 main.py`)
- [ ] Kraken CLI installed and working (`kraken balance -o json` returns balance)
- [ ] At least one position has closed (`nexus_positions.json` has entries with `status: "closed"`)
- [ ] `realised_pnl` is non-zero in `nexus_equity_curve.json`
- [ ] Equity curve shows positive or negative PnL (not alternating zeros)
- [ ] Agent weights have been updated (`nexus_weights.json` shows changing weights after trades)

---

## Quick Summary

| Issue | Symptom | Solution |
|-------|---------|----------|
| No trades executing | `[yellow]HOLD[/yellow]` repeatedly | Run with `--live` flag |
| Negative equity | Equity shows `-5.067...` | Switch to `--live` mode |
| Equity alternating | `equity: 10000` then `equity: -5` | Indicates dry-run simulation |
| Positions never close | `status: "open"` forever | Check thresholds, wait for price movement |
| Portfolio value zero | `portfolio_value_usd: 0.0` | Check Kraken CLI installation |
| Compliance blocks trades | `Trade blocked by compliance` | Verify Sharpe/leverage/volume requirements |

---

**Bottom Line**: Add the `--live` flag and monitor the first trade cycle. If it doesn't execute after 5-10 minutes, check the debug logs for the actual blocker.

