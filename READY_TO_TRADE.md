# 🎯 NEXUS Live Trading - Your Setup is Complete!

## What Was Added

```
✅ run_live.sh                    - Launcher script (executable)
✅ START_HERE.md                  - 10-second quickstart
✅ LIVE_SETUP_COMPLETE.md         - Full configuration guide  
✅ LIVE_SETUP_SUMMARY.md          - This summary
✅ LIVE_TRADING_QUICKSTART.md     - Quick reference
✅ NO_TRADES_FIX.md               - Troubleshooting
✅ PNLISSUE_DIAGNOSIS.md          - Technical deep-dive
```

---

## 🚀 START TRADING NOW

### One Command:
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
./run_live.sh --verbose
```

**That's it!** Your trading system is now:
- ✅ Executing real trades on Kraken
- ✅ Recording real PnL
- ✅ Learning and improving
- ✅ Showing real-time logs

---

## 📊 Monitor in Second Terminal

Copy & paste one of these to watch your trading live:

### **Option A: Watch Profit/Loss**
```bash
watch -n 5 'tail -5 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq ".[] | {equity, realised_pnl}"'
```

### **Option B: Watch Open Trades**
```bash
watch -n 5 'cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq ".[] | select(.status==\"open\") | {trade_id, direction, entry_price, volume}"'
```

### **Option C: Watch Agent Learning**
```bash
watch -n 5 'cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_weights.json | jq ".[] | {agent_id, weight, pnl_total, wins}"'
```

---

## 📈 What to Expect

| Time | What Happens |
|------|-------------|
| 0 min | System starts, fetches market data |
| 1-5 min | Agents analyzing |
| 5-10 min | First consensus vote |
| 10-20 min | First trade executes |
| 20-40 min | First trade closes with PnL |
| 40+ min | System improving, more trades |

---

## 🎓 Documentation Quick Links

| Document | Best For |
|----------|----------|
| `START_HERE.md` | **New users** - Read this first |
| `LIVE_SETUP_COMPLETE.md` | **Complete guide** with all options |
| `LIVE_TRADING_QUICKSTART.md` | **Quick reference** for commands |
| `NO_TRADES_FIX.md` | **Troubleshooting** when things go wrong |
| `PNLISSUE_DIAGNOSIS.md` | **Technical details** of the system |

---

## 🔧 Optional: Set Up Shell Aliases (2 minutes)

Makes running commands much easier:

```bash
# Create alias file
cat > ~/.nexus_aliases << 'EOF'
alias nexus_live='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --verbose'
alias nexus_test='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --dry-run --verbose'
alias nexus_equity='watch -n 5 "tail -10 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq \".[] | {timestamp, equity, realised_pnl}\""'
alias nexus_positions='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq \".[] | select(.status==\\\"open\\\")\""'
alias nexus_weights='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_weights.json | jq \".[] | {agent_id, weight, pnl_total}\""'
EOF

# Add to shell
echo 'source ~/.nexus_aliases' >> ~/.zshrc
source ~/.zshrc
```

Then use:
```bash
nexus_live        # Start trading
nexus_test        # Test mode
nexus_equity      # Watch profits
nexus_positions   # Watch trades
nexus_weights     # Watch learning
```

---

## ✨ Three Ways to Run

### 1. Simple Launcher (Recommended)
```bash
./run_live.sh --verbose
```

### 2. Direct Python Command
```bash
python3 main.py --live --verbose
```

### 3. With Shell Alias (If Set Up)
```bash
nexus_live
```

---

## 🎯 Common Scenarios

### Scenario 1: Want to test without real money?
```bash
./run_live.sh --dry-run --verbose
```
Simulates trades but doesn't execute on Kraken.

### Scenario 2: Want more frequent trades?
Edit `config.py`:
```python
CONFIDENCE_THRESHOLD = 0.15  # Was 0.20
TAKE_PROFIT_PCT = 2.0        # Was 5.0
```

### Scenario 3: Want faster position closes?
Edit `config.py`:
```python
LOOP_INTERVAL_SECONDS = 60   # Was 300 (check every minute)
```

### Scenario 4: See no trades after 30 minutes?
Check logs:
```bash
tail -50 nexus_debug.log | grep -E "HOLD|BUY|SELL|error"
```

---

## 📋 Pre-Trading Checklist

- [ ] Read `START_HERE.md` (2 minutes)
- [ ] Run `./run_live.sh --verbose` (takes 30 seconds)
- [ ] Open second terminal for monitoring (1 second)
- [ ] Copy one monitor command above (10 seconds)
- [ ] Wait 5-20 minutes for first trade (patient waiting!)
- [ ] Verify trade closed with PnL (5 minutes)

**Total: ~40 minutes until first real PnL** ✅

---

## ❓ FAQ

**Q: Is it really trading live?**
A: Yes! With `./run_live.sh --verbose` or `python3 main.py --live`, real trades execute on Kraken.

**Q: How do I know if it's working?**
A: Watch the equity curve. If it changes after ~20 minutes, you have your first trade.

**Q: Can I lose money?**
A: Yes, it's live trading. Start small and test with `--dry-run` first.

**Q: Why no trades yet?**
A: Could be market conditions, low confidence, or compliance blocks. Check logs with `tail -50 nexus_debug.log`.

**Q: How do I stop it?**
A: Press Ctrl+C in the terminal running the script.

**Q: How do I check my PnL?**
A: Watch the equity curve monitor or check `nexus_equity_curve.json` directly.

**Q: Can I adjust the settings?**
A: Yes! Edit `config.py` for position sizes, thresholds, timing, etc.

---

## 🚀 You're Ready!

Your autonomous trading system is now ready to execute real trades. 

**Next action:** 
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
./run_live.sh --verbose
```

Then monitor and enjoy! 📈

---

## 📞 Need Help?

1. **System not starting?** → Check `START_HERE.md`
2. **No trades appearing?** → Check `NO_TRADES_FIX.md`
3. **Want to understand more?** → Read `PNLISSUE_DIAGNOSIS.md`
4. **Full configuration guide?** → See `LIVE_SETUP_COMPLETE.md`
5. **Quick command reference?** → Use `LIVE_TRADING_QUICKSTART.md`

---

**Happy Trading! 🎉**

