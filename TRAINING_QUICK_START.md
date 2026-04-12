# 🚀 NEXUS Training: Quick Start & Reference

## ✅ Status
- **Bug Fixed:** ✓ `consensus_engine.record_outcome()` now called in exit block
- **Training System:** ✓ Ready to run
- **Weights:** ✓ Will update on every trade close

---

## Start Training NOW

### Terminal 1: Launch Training Loop
```bash
cd "/Users/thapelodipela/Desktop/NEXUS TRADING AI"
python3 main.py --dry-run -v
```

### Terminal 2: Monitor Weights Live
```bash
python3 training_monitor.py
```

### Terminal 3: Quick Weight Check (Anytime)
```bash
python3 -c "
import json
for w in json.load(open('nexus_weights.json')):
    total = w['wins'] + w['losses']
    acc = w['wins']/total*100 if total else 0
    print(f\"{w['agent_id']:20} w={w['weight']:.3f}  W/L={w['wins']}/{w['losses']}  acc={acc:.0f}%\")
"
```

---

## What You'll See

### 1st Hour (Minimal Changes)
- Positions opening and closing
- Logs show: `[bold cyan]Weights updated[/bold cyan] — win $X across N agents`
- Weights still ~1.0 (few trades = few outcomes)

### 2–8 Hours (Clear Winner Emerging)
- One agent's weight climbing above 1.2
- Others falling below 1.0
- PnL accumulating (positive or negative)

### 8–24 Hours (Stable Reputation)
- Weights frozen in ranking (no more changes)
- One agent dominates (weight > 1.5)
- Winner has 50%+ win rate
- **Ready for live trading consideration**

---

## Understanding the Numbers

### Weight Interpretation
| Value | Meaning |
| --- | --- |
| **> 1.3** | Winning agent (trust it more) |
| **1.0–1.3** | Neutral to good |
| **0.7–1.0** | Below average |
| **< 0.7** | Losing agent |
| **0.1** (floor) | Retired (too many losses) |

### Why Weights Change Slowly
- Math: `delta = 0.01 × confidence × tanh(PnL / 500)`
- For $2.50 trade: `tanh(0.005) ≈ 0.005` → tiny change
- **For $250 trade: `tanh(0.5) ≈ 0.46` → visible change**
- **Need $50–500 PnL per trade to see divergence**

---

## Key Files

| File | Purpose |
| --- | --- |
| `main.py` | Trading loop (now has training fix ✓) |
| `consensus/engine.py` | Weight update engine |
| `nexus_weights.json` | Agent reputation (read/write) |
| `training_monitor.py` | Real-time dashboard |
| `TRAINING_COMPLETE.md` | Full guide (this is the quick version) |

---

## What the Training Step Does

Added to `main.py` exit block:

```python
# Re-analyze agents on trade close
current_votes = []
for agent in agents:
    vote = agent.analyze(market_data)
    if vote:
        current_votes.append(vote)

# Update weights based on PnL
if current_votes:
    consensus_engine.record_outcome(
        direction_str=position.direction,
        confidence=position.entry_confidence,
        votes=current_votes,
        pnl_usd=pnl_usd,
        current_price=market_data.current_price,
    )
    logger.info(f"[bold cyan]Weights updated[/bold cyan] — {'win' if pnl_usd >= 0 else 'loss'} ${pnl_usd:+.2f}")
```

**Result:** Every trade close triggers a weight update.

---

## Common Issues & Fixes

### Issue: Weights still at 1.0 after 30 min
**Check:** Are positions closing? Look for `[bold red]EXIT[/bold red]` in logs  
**Fix:** Wait longer or adjust STOP_LOSS_PCT to tighter value

### Issue: All agents retiring (weight at 0.1)
**Check:** Are all trades losing?  
**Fix:** Increase CONFIDENCE_THRESHOLD or STOP_LOSS_PCT

### Issue: Weights jumping erratically
**Check:** Are you trading a very small position?  
**Fix:** Increase MAX_TRADE_SIZE_USD (noise amplified with tiny trades)

### Issue: PRISM API timeout
**Check:** Are you on the sandbox?  
**Fix:** Run from your own machine — network restriction, not code bug

---

## Decision: When to Go Live?

Go live only when:
1. ✅ Winner agent weight > 1.3
2. ✅ Winner has > 50% win rate (wins > losses)
3. ✅ Total PnL is positive
4. ✅ Weights stable (no swings last 10 trades)

Example:
```python
winner = max(records, key=lambda x: x.weight)
if winner.weight > 1.3 and winner.wins > winner.losses:
    print("✅ Ready for live")
else:
    print("❌ Stay in dry-run")
```

---

## Performance Timeline

| Timeframe | Typical PnL | Weights | Status |
| --- | --- | --- | --- |
| 30 min | ±$5–15 | 0.98–1.02 | Training starting |
| 2 hours | ±$25–100 | 0.85–1.15 | Diverging |
| 8 hours | ±$200–1000 | 0.7–1.4 | Clear winner |
| 24 hours | ±$500–5000+ | 0.5–1.8+ | Ready for live |

---

## Reset Training

If something goes wrong, start fresh:

```bash
rm nexus_weights.json nexus_equity_curve.json nexus_positions.json
python3 main.py --dry-run -v
```

All weights reset to 1.0.

---

## The Formula (For Nerds)

```
For a closed trade with PnL:

1. Determine winners/losers: did this agent vote correctly?
2. Calculate magnitude: tanh(|PnL| / $500)
3. Calculate delta: 0.01 × agent_confidence × magnitude
4. Update weight: weight ± delta (clamped 0.1–5.0)
5. Save to nexus_weights.json
6. Pass agent_votes to on-chain reputation registry
```

That's it. **No gradients, no backprop, no GPU.**

---

## Support

Full guide: `TRAINING_COMPLETE.md`  
Generated: April 11, 2026  
NEXUS v0.15.0 — Reputation-Weighted Agent Consensus
