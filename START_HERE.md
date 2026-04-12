# 🚀 NEXUS Live Trading - Start Here

## Get Trading in 10 Seconds

```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
./run_live.sh --verbose
```

**Done!** Your trading system is now live.

---

## What Just Happened

✅ Real trades executing on Kraken  
✅ Real PnL being recorded  
✅ Real agent learning happening  
✅ Real-time logs showing everything  

---

## Monitor Results (Open Second Terminal)

### See Your Profit/Loss:
```bash
watch -n 5 'tail -5 nexus_equity_curve.json | jq ".[] | {equity, realised_pnl}"'
```

### See Open Positions:
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"open\")"'
```

### See Closed Positions with PnL:
```bash
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"closed\") | {direction, pnl_usd, pnl_pct}"'
```

### See Agent Learning:
```bash
watch -n 5 'cat nexus_weights.json | jq ".[] | {agent_id, weight, pnl_total}"'
```

---

## First Trade Usually Appears Within

- ⏱️ 5-10 minutes: Agents analyzing
- 🤝 10-15 minutes: Consensus forming
- 📊 15-20 minutes: First trade executes
- ✅ 20-30 minutes: Trade closes with PnL

---

## Alternative Run Methods

**Direct command:**
```bash
python3 main.py --live --verbose
```

**Test mode (no real trades):**
```bash
./run_live.sh --dry-run --verbose
```

---

## For More Easy Commands

Set up shell aliases (one-time setup):

```bash
cat > ~/.nexus_aliases << 'EOF'
alias nexus_live='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --verbose'
alias nexus_test='cd /Users/thapelodipela/Desktop/nexus-trading-ai && ./run_live.sh --dry-run --verbose'
alias nexus_equity='watch -n 5 "tail -10 /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_equity_curve.json | jq \".[] | {equity, realised_pnl}\""'
alias nexus_positions='watch -n 5 "cat /Users/thapelodipela/Desktop/nexus-trading-ai/nexus_positions.json | jq \".[] | select(.status==\\\"open\\\")\""'
EOF

echo 'source ~/.nexus_aliases' >> ~/.zshrc
source ~/.zshrc
```

Then use:
```bash
nexus_live      # Start trading
nexus_test      # Test mode
nexus_equity    # Watch profits
nexus_positions # Watch positions
```

---

## Troubleshooting

**See no trades after 30 minutes:**
```bash
grep "HOLD\|confidence\|error" nexus_debug.log | tail -20
```

**Check Kraken is working:**
```bash
kraken balance -o json
```

**Adjust settings for more trades:**
```bash
# Edit config.py
CONFIDENCE_THRESHOLD = 0.15  # Lower from 0.20
```

---

## That's It!

Your autonomous trading system is running. Check back in 30 minutes to see your first real PnL.

**Questions?** See the detailed guides:
- `LIVE_SETUP_COMPLETE.md` - Full configuration guide
- `NO_TRADES_FIX.md` - Troubleshooting
- `PNLISSUE_DIAGNOSIS.md` - Technical details

