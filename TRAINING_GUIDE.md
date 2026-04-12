# NEXUS Training Guide

## 🎯 Three Training Options

### ✅ Option 1: Start Dry-Run Training

Run the trading system in simulation mode (no real money):

```bash
cd /Users/thapelodipela/Downloads/nexus_fixed
python3 main.py --dry-run -v
```

**What happens:**
- ✅ Trading cycles run every 300 seconds (5 minutes)
- ✅ Agents analyze market data and vote
- ✅ Consensus engine makes trading decisions
- ✅ Positions open and close based on stop-loss/take-profit rules
- ✅ Agent weights update based on trade outcomes
- ✅ Equity curve and position history are recorded

**Expected output:**
```
Cycle #1: HOLD (confidence: 0.25)
Cycle #2: BUY (confidence: 0.62)
Position opened: BUY 0.0025 BTC @ $50,100.00
Market Regime: trending | Weights: {momentum: 1.5, sentiment: 0.8, ...}
[feedback loop] momentum boosted +$123.45 (weight=1.32)
```

---

### ✅ Option 2: Check Training Status

Monitor agent learning progress:

```bash
python3 << 'EOF'
import json

with open('nexus_weights.json', 'r') as f:
    weights = json.load(f)

print("Agent Learning Status:")
print("=" * 60)
for agent in weights:
    print(f"{agent['agent_id']:20} Weight: {agent['weight']:.2f}")
    print(f"  Trades: {agent['trades_closed']} | PnL: ${agent['pnl_total']:.2f}")
    win_rate = (agent['wins']/max(agent['trades_closed'],1)*100) if agent['trades_closed'] else 0
    print(f"  Win Rate: {win_rate:.1f}%\n")
EOF
```

**Output shows:**
- Agent weights (0.1 to 5.0 scale)
- Number of closed trades
- Total profit/loss
- Win rate percentage

---

### ✅ Option 3: Real-Time Monitoring Dashboard

Watch training progress in real-time:

```bash
# Terminal 1: Start training
python3 main.py --dry-run -v

# Terminal 2: Monitor progress
python3 training_monitor.py
```

**Dashboard shows:**
- Session elapsed time
- Current portfolio equity
- Total ROI percentage
- Agent performance metrics
- Recent position history
- Win rate

---

## 📊 Training Metrics Explained

### Agent Weight (0.1 to 5.0)
- **1.0** = Initial/equal weight
- **> 1.0** = Agent is outperforming (boosted)
- **< 1.0** = Agent is underperforming (penalized)
- **< 0.1** = Agent at minimum floor

**Example:**
- Momentum: 1.8 (good performance, trades were profitable)
- Sentiment: 0.6 (underperforming, needs to improve)

### Trade Outcomes
- **Win**: Position closed at take-profit (>0 PnL)
- **Loss**: Position closed at stop-loss (<0 PnL)
- **Time-based**: Position held maximum time, closed at break-even

### Equity Curve
- Tracks portfolio value over time
- Initial: $10,000
- Updated after each position closes
- Used for Sharpe ratio calculation

---

## 📈 What to Expect

### First 30 Minutes (6 cycles)
- Agents start with equal weights (1.0)
- Some trades may be blocked by compliance checks
- Positions start to accumulate
- Regime detection activates

### First 2 Hours (24 cycles)
- Agent weights begin to diverge
- Clear winners and underperformers emerge
- Position history grows
- Equity curve shows trend

### First 8 Hours (96 cycles)
- Significant weight differentiation
- Some agents may approach retirement
- Clear performance patterns visible
- Good baseline for live trading decision

---

## 🚀 Recommended Training Duration

| Duration | Training Cycles | Use Case |
|----------|-----------------|----------|
| **30 min** | 6 | Quick sanity check |
| **2 hours** | 24 | Initial weight calibration |
| **8 hours** | 96 | Before live trading |
| **24 hours** | 288 | Full performance baseline |
| **1 week** | 2,016 | Comprehensive learning |

---

## 📝 Training Files Generated

During training, these files are created/updated:

```
nexus_weights.json         # Agent weights and statistics
nexus_equity_curve.json    # Portfolio value over time
nexus_positions.json       # Trade history and outcomes
```

**Example nexus_weights.json:**
```json
[
  {
    "agent_id": "momentum",
    "weight": 1.45,
    "trades_closed": 12,
    "pnl_total": 234.56,
    "wins": 8,
    "losses": 4,
    "retired": false
  },
  ...
]
```

---

## 🔧 Configuration for Training

Edit these in `config.py` or `.env`:

```bash
# Training Settings
LOOP_INTERVAL_SECONDS=300          # Cycle every 5 minutes
RISK_PCT_PER_TRADE=0.01           # 1% risk per trade
MIN_TRADE_SIZE_USD=10.0           # Minimum $10
MAX_TRADE_SIZE_USD=500.0          # Maximum $500

# Exit Conditions
TAKE_PROFIT_PCT=5.0               # Close if up 5%
STOP_LOSS_PCT=2.0                 # Close if down 2%
MAX_HOLD_TIME_MINUTES=1440        # Hold max 24 hours

# Learning
WEIGHT_LEARN_RATE=0.1             # How quickly weights adjust
CONFIDENCE_THRESHOLD=0.55         # Need 55% confidence to trade
```

---

## 🎮 Interactive Training Session

```bash
# Start training with verbose logging
python3 main.py --dry-run -v

# In another terminal, monitor in real-time
python3 training_monitor.py

# Check specific agent performance
python3 -c "import json; print(json.dumps(json.load(open('nexus_weights.json')), indent=2))"

# View equity curve
tail -20 nexus_equity_curve.json | python3 -m json.tool

# View position history
tail -20 nexus_positions.json | python3 -m json.tool
```

---

## 💡 Tips for Effective Training

1. **Run continuously**: Let it train for at least 2-4 hours for meaningful data
2. **Monitor real-time**: Use `training_monitor.py` to see progress
3. **Check weights regularly**: See which agents are learning
4. **Review positions**: Understand which trades worked/failed
5. **Adjust if needed**: Modify config between runs to test variations

---

## ⚠️ Common Issues

### Training not progressing
- Check that PRISM API key is valid (run `python3 main.py --ping`)
- Verify Kraken portfolio has funds (even in dry-run, simulated)

### Agent weights not updating
- Need multiple completed positions (trades close after 5-24h hold)
- Check `nexus_positions.json` for closed trades

### Consensus always HOLD
- This is normal early in training
- Agents are calibrating, confidence threshold is 0.55
- Will improve as market regime is detected

---

## 🎯 Next Steps

1. **Start dry-run training**: `python3 main.py --dry-run -v`
2. **Monitor progress**: `python3 training_monitor.py`
3. **Let it train for 8+ hours**
4. **Review agent weights** and results
5. **Deploy to live trading** when confident

Good luck! 🚀
