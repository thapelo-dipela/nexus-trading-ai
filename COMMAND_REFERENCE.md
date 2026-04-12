# NEXUS Live Trading - Command Reference Card

## 🚀 Start Trading

```bash
# Live mode (real trades)
./run_live.sh --verbose

# Alternative (direct command)
python3 main.py --live --verbose

# Test mode (no real trades)
./run_live.sh --dry-run --verbose
```

---

## 📊 Monitor Trading (Run in Separate Terminal)

### Watch Your Profit/Loss
```bash
watch -n 5 'tail -5 nexus_equity_curve.json | jq ".[] | {equity, realised_pnl}"'
```

### Watch Open Positions
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"open\") | {trade_id, direction, entry_price, volume}"'
```

### Watch Closed Positions with PnL
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"closed\") | {direction, pnl_usd, pnl_pct, exit_reason}"'
```

### Watch Agent Learning
```bash
watch -n 5 'cat nexus_weights.json | jq ".[] | {agent_id, weight, pnl_total, wins, losses}"'
```

### Watch Live Logs
```bash
tail -f nexus_debug.log
```

---

## 🔍 Quick Checks

### Verify Kraken is working
```bash
kraken balance -o json
kraken ticker -o json XXBTZUSD
```

### Check recent trades
```bash
cat nexus_positions.json | jq '.[] | select(.status=="closed")' | tail -5
```

### Check current equity
```bash
tail -1 nexus_equity_curve.json | jq '.'
```

### Check agent weights (learning)
```bash
cat nexus_weights.json | jq '.[] | {agent_id, weight}'
```

### Look for errors
```bash
grep -i "error\|failed" nexus_debug.log | tail -10
```

---

## ⚙️ Configuration Adjustments

**File:** `config.py`

### More Frequent Trades
```python
CONFIDENCE_THRESHOLD = 0.15        # Down from 0.20
TAKE_PROFIT_PCT = 2.0              # Down from 5.0
STOP_LOSS_PCT = 1.0                # Down from 2.0
```

### Larger Positions
```python
MIN_TRADE_SIZE_USD = 50.0           # Up from 10.0
MAX_TRADE_SIZE_USD = 1000.0         # Up from 500.0
```

### Faster Checks (Testing Only)
```python
LOOP_INTERVAL_SECONDS = 60          # Down from 300
```

### Longer Holds
```python
MAX_HOLD_TIME_MINUTES = 2880        # Up from 1440
```

---

## 🎯 Test Your Setup

### Verify Script is Executable
```bash
ls -lh run_live.sh
# Should show: -rwxr-xr-x
```

### Quick 30-Second Test
```bash
./run_live.sh --dry-run --verbose &
sleep 30
kill %1
tail nexus_debug.log
```

### Check All Documentation
```bash
ls -1 *.md | grep -E "START|LIVE|READY|NO_TRADES"
```

---

## 🆘 Troubleshooting Quick Commands

### No trades appearing?
```bash
grep "HOLD\|BUY\|SELL\|confidence" nexus_debug.log | tail -20
```

### Check confidence levels
```bash
grep "confidence" nexus_debug.log | tail -5
```

### Check compliance blocks
```bash
grep "Trade blocked" nexus_debug.log
```

### Check Kraken errors
```bash
grep -i "kraken.*error" nexus_debug.log
```

### See last 5 trades executed
```bash
cat nexus_positions.json | jq '.[] | select(.status=="closed")' | tail -10
```

---

## 📱 Shell Aliases Setup (Optional)

```bash
# Create alias file
cat > ~/.nexus_aliases << 'EOF'
alias nexus_live='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --verbose'
alias nexus_test='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --dry-run --verbose'
alias nexus_equity='watch -n 5 "tail -10 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq \".[] | {equity, realised_pnl}\""'
alias nexus_positions='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq \".[] | select(.status==\\\"open\\\")\""'
alias nexus_weights='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_weights.json | jq \".[] | {agent_id, weight, pnl_total}\""'
alias nexus_cd='cd /Users/thapelodipela/Desktop/nexus-trading-ai'
EOF

# Add to shell config
echo 'source ~/.nexus_aliases' >> ~/.zshrc
source ~/.zshrc
```

Then use:
```bash
nexus_live          # Start trading
nexus_test          # Test mode
nexus_equity        # Watch profits
nexus_positions     # Watch trades
nexus_weights       # Watch learning
nexus_cd            # Go to folder
```

---

## 📚 Documentation Map

| Command | Docs to Read |
|---------|-------------|
| `./run_live.sh --verbose` | START_HERE.md |
| Want full guide? | LIVE_SETUP_COMPLETE.md |
| System not working? | NO_TRADES_FIX.md |
| What went wrong? | PNLISSUE_DIAGNOSIS.md |
| Quick reference? | LIVE_TRADING_QUICKSTART.md |
| Visual overview? | READY_TO_TRADE.md |

---

## ⏱️ Expected Timeline

```
0 min:    System starts → fetches market data
5 min:    Agents analyzing price data
10 min:   First consensus vote
15-20 min: First BUY/SELL signal → trade executes
20-40 min: Position held → stop-loss/take-profit triggers
40+ min:  Position closed with real PnL ✨
45+ min:  System learns → agent weights update
60+ min:  Second trade cycle begins
```

---

## ✅ Pre-Trading Checklist

- [ ] Ran `./run_live.sh --verbose` once to verify it works
- [ ] Kraken CLI installed (`kraken --version` returns version)
- [ ] Kraken connectivity verified (`kraken balance -o json` works)
- [ ] Monitor command ready to go (copied above)
- [ ] Second terminal open for monitoring
- [ ] Ready to wait 20-40 minutes for first trade
- [ ] Understand dry-run vs live mode

---

## 🚀 Ready? Go Trade!

```bash
./run_live.sh --verbose
```

Monitor in another terminal. First real PnL in ~20 minutes! 📈

