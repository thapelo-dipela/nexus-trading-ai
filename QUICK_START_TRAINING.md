# 🚀 TRAINING RESUMPTION GUIDE

**Status:** ✅ All systems ready  
**Migration:** Completed (CryptoPanic → 4-source sentiment)  
**Date:** 2025-01-20

---

## ⚡ Quick Start

### Terminal 1: Start Training Loop
```bash
cd "/Users/thapelodipela/Desktop/NEXUS TRADING AI"
python3 main.py --dry-run -v
```

**Expected output (first 30 seconds):**
```
[bold green]Starting NEXUS live trading engine[/bold green]
[green]Loaded weights for 4 agents[/green]
[bold blue]Position Manager[/bold blue]: Stop-loss/take-profit exits with feedback loop
[bold blue]Regime Detector[/bold blue]: Market regime classification with dynamic re-weighting
[bold blue]Compliance Engine[/bold blue]: Best Compliance & Risk Guardrails
[bold blue]Validation Engine[/bold blue]: Best Trustless Trading Agent & Validation Model
[bold blue]Yield Optimizer[/bold blue]: Best Yield & Risk-Adjusted Returns

[bold]Cycle #1[/bold]
Fetching market data...
[dim]Fear/Greed: 65/100 → signal=+0.30[/dim]
[dim]CoinGecko trending: BTC #4 → signal=-0.10[/dim]
[dim]CoinGecko community: up=55.0% → signal=+0.10[/dim]
[dim]Messari 24h change: +2.50% → signal=+0.25[/dim]
[dim]Sentiment blend (...): +0.488[/dim]

Agent votes:
  momentum: BUY (0.65)
  sentiment: HOLD (0.10)
  risk_guardian: VETO (risk_score=80 >= 75)
  mean_reversion: HOLD (0.25)

Consensus: HOLD (veto by risk_guardian)
```

### Terminal 2: Monitor Training Progress
```bash
python3 training_monitor.py
```

**Expected output (updates every 5 minutes):**
```
╭─ NEXUS Training Monitor ──────────────────────────────────────────╮
│ Cycle: 12 | Elapsed: 60 min                                       │
│ Last trade: BUY $1000 (closed: $2.50 profit)                     │
│ Agent Reputation:                                                 │
│   momentum:     1.02 (↑) | 4 trades | +$12.50 PnL                │
│   sentiment:    0.98 (↓) | 3 trades | -$2.50 PnL                │
│   risk_guardian: 0.99    | 1 veto   | 0 trades                   │
│   mean_reversion: 0.96   | 3 trades | -$8.00 PnL               │
╰────────────────────────────────────────────────────────────────────╯
```

---

## 📊 What to Watch For

### Sentiment Logs (Verify 4 sources are live)
Look for lines like:
```
[dim]Fear/Greed: 65/100 → signal=+0.30[/dim]
[dim]CoinGecko trending: BTC #4 → signal=-0.10[/dim]
[dim]CoinGecko community: up=55.0% → signal=+0.10[/dim]
[dim]Messari 24h change: +2.50% → signal=+0.25[/dim]
[dim]Sentiment blend (fear_greed, trending, community, messari_momentum): +0.488[/dim]
```

✅ All 4 sources shown = Multi-source system working  
⚠️ Some sources missing = Single source failed (graceful fallback active)  
❌ No sentiment logs = fetch_composite_sentiment() not being called

### Weight Updates (Training feedback loop active)
Look for lines like:
```
[bold cyan]Weights updated[/bold cyan] — win $2.50 for momentum, loss $1.00 for sentiment
```

✅ Weights changing = Learning is happening  
⚠️ Weights stuck at 1.0 = Bug: record_outcome() not called (training broken)

### Risk Veto Messages
```
risk_guardian: VETO (risk_score=80.0 >= 75.0 threshold)
```

✅ Occasional veto = Working as designed  
⚠️ Every cycle = Market too volatile, trading disabled  
❌ No veto = Risk assessment broken

---

## 🎯 Training Timeline

| Time | Expected Activity |
|------|-------------------|
| 0-5 min | System startup, first cycle |
| 5-30 min | First trades opening/closing, weights start changing |
| 30 min - 4 hours | Agent divergence becomes visible (some weights > 1.05, others < 0.95) |
| 4-24 hours | Significant weight spread (winners 1.1+, losers 0.9-) |
| 24-72 hours | Market regime changes, agents re-weight dynamically |

---

## 🔧 Troubleshooting

### "Fear/Greed fetch failed"
- One source failed (acceptable)
- If ALL sources fail: check internet connection

### "Weights stuck at 1.0"
- Bug: `record_outcome()` not being called when positions close
- **Solution:** This was fixed. Check main.py lines 195-220 have the training step.

### "Risk score always 100"
- PRISM API not returning volatility data
- Check: `python3 main.py --ping` to verify connectivity

### "No trades opening"
- Normal if market is neutral or risk is high
- Check logs for "HOLD" consensus or risk veto

---

## 📈 Success Metrics (After 24-48 hours)

- ✅ **Weights diverged**: Some agents > 1.05, others < 0.95
- ✅ **Trades closed**: At least 5-10 positions closed (monitored in nexus_weights.json)
- ✅ **PnL recorded**: nexus_weights.json shows non-zero win/loss counts
- ✅ **No CryptoPanic errors**: Logs clean of "News sentiment fetch failed"
- ✅ **Sentiment blend active**: All 4 sources visible in logs

---

## 📁 Key Files to Monitor

| File | Purpose | Update Frequency |
|------|---------|-----------------|
| `nexus_weights.json` | Agent reputation tracking | Each trade close |
| `positions.json` | Open positions | Real-time |
| `.log` (if enabled) | System logs | Every cycle |
| `submissions.json` | Performance history | Each cycle |

---

## 🛑 Graceful Shutdown

When ready to stop:
```bash
Ctrl+C
```

System will:
1. Save current positions to `positions.json`
2. Record final state in `nexus_weights.json`
3. Exit cleanly

Resume training later by running `python3 main.py --dry-run -v` again.

---

## 📝 Notes

- Training runs in `--dry-run` mode (no live Kraken execution)
- Each cycle: 5 minutes (300 seconds)
- Market data: Live from PRISM API (verified at startup)
- Sentiment: 4 free APIs, multi-source blend
- Consensus: Reputation-weighted agent voting
- Risk: 75.0 risk_score threshold (blocks trades)

---

**Ready to begin training! Start Terminal 1 with `python3 main.py --dry-run -v`**
