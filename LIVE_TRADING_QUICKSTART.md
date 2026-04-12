# NEXUS Live Trading - Quick Start

## 🚀 Start Live Trading (3 Ways)

### Option 1: Using the Launcher Script (Recommended ✅)
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
./run_live.sh --verbose
```

**Features:**
- ✅ Automatic mode detection
- ✅ Simple, easy to remember
- ✅ Built-in error checking
- ✅ Add `--verbose` for detailed logs
- ✅ Add `--dry-run` to test without real trades

---

### Option 2: Direct Command
```bash
python3 main.py --live --verbose
```

**Flags:**
- `--live` → Execute real trades on Kraken
- `--verbose` → Enable debug logging
- `--dry-run` → Simulate trades (default if no flag)

---

### Option 3: For Testing Only (Dry-Run Mode)
```bash
./run_live.sh --dry-run --verbose
```

This simulates trades without executing on Kraken. Useful for:
- Testing agent logic
- Checking compliance rules
- Verifying PnL calculations (will be fake)

---

## 📊 Monitor Trading in Real-Time

**In a separate terminal, watch the equity curve:**
```bash
watch -n 5 'tail -10 nexus_equity_curve.json | jq ".[] | {timestamp, equity, cash, realised_pnl}"'
```

**Monitor open positions:**
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"open\")"'
```

**Watch closed positions (PnL results):**
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"closed\") | {trade_id, direction, pnl_usd, pnl_pct}"'
```

**Check agent weights (learning progress):**
```bash
watch -n 5 'cat nexus_weights.json | jq ".[] | {agent_id, weight, pnl_total}"'
```

---

## 🔍 What to Expect

### First 5 Minutes:
```
✅ Market data loading from PRISM
✅ Agents analyzing price action
✅ Consensus voting on BUY/SELL/HOLD
⏳ First trade may take 1-2 cycles to execute
```

### After First Trade Opens:
```
✅ Position recorded in nexus_positions.json
✅ Equity curve shows unrealised PnL
✅ System monitors stop-loss/take-profit
```

### After Trade Closes:
```
✅ Position marked as "closed"
✅ Realised PnL recorded
✅ Agent weights updated based on outcome
✅ Equity curve updated with net result
```

---

## ⚠️ Common Issues & Fixes

### Issue: "Kraken balance command failed"
**Solution:**
```bash
# Check if Kraken CLI is installed
kraken --version

# If not installed:
brew install kraken-cli  # macOS
# or
apt-get install kraken-cli  # Linux
```

---

### Issue: "HOLD" repeated in logs (no trades executing)
**Causes:**
1. Confidence too low (agents not agreeing)
2. Market conditions not favorable
3. Compliance rules blocking trades

**Check confidence:**
```bash
grep "confidence" -A2 -B2 trading_session.log | head -20
```

**Lower threshold to allow more trades (config.py):**
```python
CONFIDENCE_THRESHOLD = 0.15  # Lower from 0.20
```

---

### Issue: Equity shows negative values
**This indicates:**
- Running in simulation only (not `--live`)
- Position manager calculation issue

**Fix:**
- Make sure you're using `./run_live.sh` or `python3 main.py --live`
- Not just `python3 main.py` (defaults to dry-run)

---

## 📈 Understanding the Equity Curve

**Healthy pattern:**
```json
equity: 10000.0  (initial)
↓
equity: 9950.0   (position opened, price moved against)
↓
equity: 10045.0  (position closed, net +$45 profit)
```

**Problem pattern:**
```json
equity: 10000.0
↓
equity: -5.07    ❌ NEGATIVE EQUITY (impossible)
```
→ Indicates dry-run mode or calculation bug

---

## 🛠️ Configuration Tuning

**File:** `config.py`

### For More Frequent Trades:
```python
CONFIDENCE_THRESHOLD = 0.15        # Down from 0.20
TAKE_PROFIT_PCT = 2.0              # Down from 5.0
STOP_LOSS_PCT = 1.0                # Down from 2.0
```

### For Larger Position Sizes:
```python
MIN_TRADE_SIZE_USD = 50.0           # Up from 10.0
MAX_TRADE_SIZE_USD = 1000.0         # Up from 500.0
RISK_PCT_PER_TRADE = 0.02           # Up from 0.01
```

### For Longer Holds:
```python
MAX_HOLD_TIME_MINUTES = 2880        # Up from 1440 (2 days instead of 1 day)
```

---

## ✅ Verification Checklist

Before declaring the system working:

- [ ] Running with `./run_live.sh --verbose` or `python3 main.py --live`
- [ ] No "Kraken balance command failed" errors
- [ ] Logs show agent votes (BUY/SELL with confidence)
- [ ] At least one trade has executed (position in nexus_positions.json)
- [ ] Position closed with real PnL (not zero)
- [ ] Equity curve shows non-negative values
- [ ] Agent weights have changed (learning happening)

---

## 🚦 Trading Loop Intervals

**Default:** Every 5 minutes (`LOOP_INTERVAL_SECONDS = 300`)

This means:
- New price data fetched every 5 minutes
- Agents analyze every 5 minutes
- Positions checked for exit every 5 minutes
- A trade may take 5-15 minutes from entry to first exit check

To speed up testing:
```python
# config.py
LOOP_INTERVAL_SECONDS = 30  # Check every 30 seconds (testing only!)
```

⚠️ **Warning:** Faster intervals = more API calls, higher costs. Use for testing only.

---

## 📞 Support

If trades still aren't executing:

1. Check verbose logs:
   ```bash
   ./run_live.sh --verbose 2>&1 | tee debug.log
   ```

2. Look for these specific issues:
   ```bash
   grep -i "error\|blocked\|hold\|veto" debug.log
   ```

3. Verify Kraken connectivity:
   ```bash
   kraken balance -o json
   kraken ticker -o json XXBTZUSD
   ```

4. Check agent analysis:
   ```bash
   grep "agent_id.*confidence" debug.log
   ```

---

## 🎯 Next Steps

1. **Start trading:** `./run_live.sh --verbose`
2. **Monitor equity:** Open second terminal and run watch commands above
3. **Wait for first trade:** Usually within 10-20 minutes
4. **Verify PnL:** Check closed positions and weights update
5. **Tune if needed:** Adjust config.py thresholds for more/fewer trades

**That's it!** The system will now:
- ✅ Execute real trades on Kraken
- ✅ Track positions and PnL
- ✅ Update agent weights based on results
- ✅ Continuously improve over time

