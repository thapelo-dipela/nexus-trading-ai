# NEXUS Live Trading - Complete Setup Guide

## ✅ Quick Start (Copy & Paste)

### Start Live Trading NOW:
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
./run_live.sh --verbose
```

That's it! The system is now:
- ✅ Executing real trades on Kraken
- ✅ Recording PnL in real-time
- ✅ Learning and improving agent weights
- ✅ Displaying detailed logs

---

## 🎯 Three Ways to Run

### 1️⃣ Simple Launcher Script (Recommended)
```bash
./run_live.sh --verbose
```
- Most reliable
- Automatic error checking
- Clear output

### 2️⃣ Direct Python Command
```bash
python3 main.py --live --verbose
```
- Direct control
- Full command visibility

### 3️⃣ Dry-Run Testing (No Real Trades)
```bash
./run_live.sh --dry-run --verbose
```
- Test without risking capital
- Verify logic before going live

---

## 📊 Real-Time Monitoring (Open in Separate Terminals)

### Monitor 1: Equity Curve (Portfolio Value)
```bash
watch -n 5 'tail -10 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq ".[] | {timestamp, equity, cash, realised_pnl}"'
```
**Shows:** Total portfolio value over time

### Monitor 2: Open Positions
```bash
watch -n 5 'cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq ".[] | select(.status==\"open\") | {trade_id, direction, entry_price, volume, entry_confidence}"'
```
**Shows:** Currently open trades and entry details

### Monitor 3: Closed Positions (PnL)
```bash
watch -n 5 'cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq ".[] | select(.status==\"closed\") | {trade_id, direction, pnl_usd, pnl_pct, exit_reason}"'
```
**Shows:** Completed trades with realized PnL

### Monitor 4: Agent Learning (Weights)
```bash
watch -n 5 'cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_weights.json | jq ".[] | {agent_id, weight, pnl_total, trades_closed, win_rate_pct}"'
```
**Shows:** How each agent is learning and improving

### Monitor 5: Live Logs
```bash
tail -f /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_debug.log
```
**Shows:** Real-time trading events and decisions

---

## ⚡ Install Shell Aliases (Optional but Recommended)

These make running commands much easier:

### Step 1: Create alias file
```bash
cat > ~/.nexus_aliases << 'EOF'
alias nexus_live='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --verbose'
alias nexus_test='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --dry-run --verbose'
alias nexus_equity='watch -n 5 "tail -10 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq \".[] | {timestamp, equity, cash, realised_pnl}\""'
alias nexus_positions='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq \".[] | select(.status==\\\"open\\\") | {trade_id, direction, entry_price, volume}\""'
alias nexus_weights='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_weights.json | jq \".[] | {agent_id, weight, pnl_total}\""'
alias nexus_cd='cd /Users/thapelodipela/Desktop/nexus-trading-ai'
EOF
```

### Step 2: Add to shell configuration
```bash
echo 'source ~/.nexus_aliases' >> ~/.zshrc
```

### Step 3: Reload shell
```bash
source ~/.zshrc
```

### Now use simple commands:
```bash
nexus_live        # Start live trading
nexus_test        # Test dry-run
nexus_equity      # Watch equity curve
nexus_positions   # Watch open positions
nexus_weights     # Watch agent learning
nexus_cd          # Go to nexus folder
```

---

## 🔄 What Happens Each Cycle (Every 5 Minutes)

1. **Fetch Market Data** (5 sec)
   - Price from PRISM API
   - OHLCV candles
   - Risk metrics
   - Fear & Greed index

2. **Agent Analysis** (2 sec)
   - Momentum Agent votes
   - Mean Reversion Agent votes
   - Sentiment Agent votes
   - Risk Guardian votes

3. **Consensus Vote** (1 sec)
   - Agents vote: BUY / SELL / HOLD
   - System computes consensus
   - Confidence threshold checked

4. **Risk Checks** (1 sec)
   - Compliance validation
   - Position sizing
   - Sharpe ratio check
   - Max leverage check

5. **Trade Execution** (2 sec)
   - If BUY/SELL: Market order on Kraken
   - Position recorded
   - Entry confidence stored

6. **Position Management** (1 sec)
   - Check all open positions
   - Stop-loss triggered?
   - Take-profit triggered?
   - Time-based exit?

7. **Training Update** (1 sec)
   - Closed trades analyzed
   - Agent weights updated
   - Feedback loop active

8. **Record Equity** (1 sec)
   - Portfolio value calculated
   - Equity curve updated
   - Metrics logged

**Total cycle time:** ~13 seconds (then sleep 5 minutes)

---

## 📈 Expected Results

### First Hour:
- Market data loading ✅
- Agent votes appearing in logs ✅
- First trade may execute ✅

### After First Trade Opens:
- Position visible in `nexus_positions.json` ✅
- Equity curve shows unrealised PnL ✅
- Real-time P&L updated each cycle ✅

### After First Trade Closes:
- Position status changes to "closed" ✅
- `pnl_usd` and `pnl_pct` populated ✅
- Agent weights updated ✅
- Realised PnL in equity curve ✅

### Over Several Hours:
- Multiple trades executed ✅
- Agent weights converging (best agents get higher weight) ✅
- Portfolio equity trend visible ✅
- Win rate and profit factor improving ✅

---

## 🐛 Troubleshooting

### Problem: "Command not found: kraken"
```bash
# Install Kraken CLI
brew install kraken-cli

# Verify
kraken --version
```

### Problem: "HOLD" in logs repeatedly
**Meaning:** Agents aren't generating BUY/SELL signals strongly enough

**Solutions:**
1. Lower confidence threshold in `config.py`:
   ```python
   CONFIDENCE_THRESHOLD = 0.15  # Was 0.20
   ```

2. Wait longer (15-20 minutes for good setups)

3. Check agent votes in logs:
   ```bash
   grep "confidence" nexus_debug.log
   ```

### Problem: Equity shows negative values
**Meaning:** Probably still in dry-run mode

**Solution:**
- Make sure using `./run_live.sh --verbose` or `python3 main.py --live`
- Not just `python3 main.py` (defaults to dry-run)

### Problem: Position opens but never closes
**Meaning:** Price hasn't hit stop-loss or take-profit

**Solutions:**
1. Lower thresholds in `config.py`:
   ```python
   TAKE_PROFIT_PCT = 2.0   # Was 5.0
   STOP_LOSS_PCT = 1.0     # Was 2.0
   ```

2. Increase loop frequency (testing only):
   ```python
   LOOP_INTERVAL_SECONDS = 30  # Was 300 (5 min)
   ```

3. Wait for price to move (market dependent)

### Problem: No positions created at all
**Meaning:** Consensus never reaches HOLD → BUY/SELL

**Causes:**
1. All agents voting HOLD
2. Confidence threshold too high
3. Compliance rules blocking

**Debug:**
```bash
grep "vote\|HOLD\|BUY\|SELL" nexus_debug.log | head -20
```

---

## 📊 Key Files to Monitor

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `nexus_positions.json` | Open/closed positions | Every cycle |
| `nexus_equity_curve.json` | Portfolio value history | Every cycle |
| `nexus_weights.json` | Agent learning progress | When trades close |
| `nexus_debug.log` | Detailed trading logs | Every cycle |

---

## 🎓 Configuration Tuning

### For More Aggressive Trading:
```python
# config.py
CONFIDENCE_THRESHOLD = 0.10         # Lower threshold
TAKE_PROFIT_PCT = 2.0               # Close sooner at profit
STOP_LOSS_PCT = 1.0                 # Close sooner at loss
MAX_TRADE_SIZE_USD = 2000.0          # Bigger positions
```

### For Conservative Trading:
```python
# config.py
CONFIDENCE_THRESHOLD = 0.30          # Higher threshold
TAKE_PROFIT_PCT = 10.0               # Hold longer for bigger gains
STOP_LOSS_PCT = 5.0                  # Accept larger losses
MIN_TRADE_SIZE_USD = 5.0             # Smaller positions
```

### For Testing/Learning:
```python
# config.py
LOOP_INTERVAL_SECONDS = 60           # Check every 1 minute (not 5)
TAKE_PROFIT_PCT = 1.0                # Close very quickly
STOP_LOSS_PCT = 0.5                  # Tight stops
```

---

## ✅ Final Checklist Before Going Live

- [ ] Ran `./run_live.sh --verbose` (not dry-run)
- [ ] Kraken CLI installed and working (`kraken balance -o json` returns data)
- [ ] Terminal showing real-time logs
- [ ] Monitoring equity curve in separate terminal
- [ ] Waiting 5-20 minutes for first trade signal
- [ ] First trade executed with real PnL
- [ ] Closed position shows non-zero `pnl_usd`
- [ ] Agent weights updated in `nexus_weights.json`
- [ ] No errors in logs about Kraken connectivity

---

## 🚀 You're Ready!

Your NEXUS trading system is now:

✅ **Executing real trades** on Kraken  
✅ **Tracking positions** with accurate PnL  
✅ **Recording equity history** for performance analysis  
✅ **Learning and improving** with feedback loop  
✅ **Fully automated** 24/7 operation  

Start with:
```bash
./run_live.sh --verbose
```

Then monitor equity and enjoy real trading! 📈

