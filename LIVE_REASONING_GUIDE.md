# NEXUS Dashboard - Live Agent Reasoning & Positions

## ✅ What's Now Live

Your dashboard now displays **real-time agent decisions with full reasoning** and **live position tracking with P&L**.

## 🎯 New Dashboard Sections

### 1️⃣ Live Agent Decisions Panel
Displays what each agent is thinking in real-time:

```
🤖 Live Agent Decisions

📈 momentum: BUY
   Conf: 70.0%
   Regime Mult: 1.5x
   RSI below 30, MACD bullish crossover, Bollinger touching lower band

🟢 sentiment: BUY
   Conf: 100.0%
   Regime Mult: 0.8x
   Fear & Greed 35 (Fear), Community trending positive

🛡️ risk_guardian: HOLD
   Conf: 100.0%
   Regime Mult: 1.0x
   PRISM risk_score 80.0 >= 75.0 threshold - VETO

⏸️ mean_reversion: HOLD
   Conf: 10.0%
   Regime Mult: 0.5x
   Price not sufficiently extended from mean
```

**What You Can See:**
- ✅ Each agent's decision (BUY/SELL/HOLD)
- ✅ Confidence level (0-100%)
- ✅ Regime multiplier applied (affects voting weight)
- ✅ Technical reasoning behind each decision
- ✅ Color-coded by direction (green=BUY, red=SELL, blue=HOLD)

### 2️⃣ Open Positions & Reasoning Panel
Displays all live positions with full context:

```
📍 Open Positions & Reasoning

📈 LONG Position #1
Entry: $45,230.50
Current: $45,892.30
Size: $500.00
PnL: +1.46%
📌 Consensus signal - momentum 1.5x boost, trending market

📉 SHORT Position #2
Entry: $45,500.00
Current: $45,200.00
Size: $250.00
PnL: +0.66%
📌 Mean reversion setup - price 2σ above 20d MA
```

**What You Can See:**
- ✅ All open positions (LONG/SHORT)
- ✅ Entry price vs current price
- ✅ Position size in USD
- ✅ Unrealized P&L percentage
- ✅ Reason position was opened
- ✅ Updates as prices change in real-time

## 🔌 Technical Implementation

### Backend (main.py)
```python
# New function saves decisions every cycle
save_live_decisions(
    cycle_num,
    agent_decisions=[
        {
            'agent_id': 'momentum',
            'direction': 'BUY',
            'confidence': 0.70,
            'regime_multiplier': 1.5,
            'reasoning': 'RSI < 30, MACD bullish'
        },
        ...
    ],
    consensus_direction=VoteDirection.HOLD,
    consensus_confidence=0.252,
    positions=[
        {
            'trade_id': 'nexus_...',
            'direction': 'LONG',
            'entry_price': 45230.50,
            'current_price': 45892.30,
            'unrealised_pnl_pct': 1.46,
            'size': 500.00,
            'reason_opened': 'Consensus signal'
        }
    ],
    recent_closes=[]
)
```

### API Endpoint (dashboard_server.py)
```python
@app.route('/api/live-decisions', methods=['GET'])
def get_live_decisions():
    """Get live agent decisions and position reasoning"""
    # Returns nexus_live_decisions.json with:
    # - Agent voting data with reasoning
    # - Consensus direction and confidence
    # - All open positions with P&L
```

### Frontend (dashboard.html)
```javascript
// New functions
fetchLiveDecisions()  // Fetches from /api/live-decisions
displayAgentDecisions(decisions)  // Renders agent panel
displayPositions(positions)  // Renders position panel

// Integrated into updateAllData()
// Updates every refresh (manual or auto)
```

### Data File (nexus_live_decisions.json)
```json
{
  "latest_cycle": 3,
  "agent_decisions": [
    {
      "agent_id": "momentum",
      "direction": "BUY",
      "confidence": 0.70,
      "regime_multiplier": 1.5,
      "reasoning": "RSI < 30, MACD bullish"
    },
    ...
  ],
  "consensus_decision": {
    "direction": "HOLD",
    "confidence": 0.252
  },
  "positions": [
    {
      "trade_id": "nexus_...",
      "direction": "LONG",
      "entry_price": 45230.50,
      "current_price": 45892.30,
      "unrealised_pnl_pct": 1.46,
      "size": 500.00,
      "reason_opened": "Consensus signal"
    }
  ],
  "recent_closes": [],
  "timestamp": "2026-04-12T15:45:00.123456"
}
```

## 📊 Data Flow

```
main.py (Trading Loop)
   ↓
[Cycle #N]
   ↓
1. Agents analyze market
   ├─ momentum → vote + reasoning
   ├─ sentiment → vote + reasoning
   ├─ risk_guardian → vote + reasoning
   └─ mean_reversion → vote + reasoning
   ↓
2. Consensus aggregates votes
   ├─ Direction (BUY/SELL/HOLD)
   ├─ Confidence score
   └─ Weighted votes
   ↓
3. Load open positions
   ├─ Entry prices
   ├─ Current prices
   ├─ P&L calculations
   └─ Opening reasons
   ↓
4. save_live_decisions()
   └─ Write to nexus_live_decisions.json
   ↓
dashboard_server.py
   ↓
GET /api/live-decisions
   └─ Return JSON with decisions + positions
   ↓
dashboard.html
   ↓
fetchLiveDecisions()
   ├─ displayAgentDecisions()  → Left panel
   └─ displayPositions()       → Right panel
   ↓
Browser Display
   ├─ Color-coded agent votes
   ├─ Reasoning text
   ├─ Position P&L
   └─ Live updates on refresh
```

## 🎬 Video Demo Tips

When recording, show:

1. **Agent Thinking:**
   - Open browser to http://localhost:3000
   - Show the "Live Agent Decisions" panel
   - Click refresh button (🔄)
   - All 4 agents show their current votes with reasoning
   - Explain each agent's strategy

2. **Consensus Voting:**
   - Show how agent votes aggregate to consensus
   - Explain confidence threshold check
   - Demonstrate Risk Guardian veto mechanism

3. **Position Management:**
   - Show "Open Positions & Reasoning" panel
   - Display entry vs current prices
   - Show unrealized P&L calculations
   - Explain why position was opened

4. **Market Regime:**
   - Toggle market regime (trending/ranging/volatile)
   - Show how regime multipliers change agent weights
   - Demonstrate adaptive weighting in action

5. **Live Updates:**
   - Click refresh multiple times to show data flowing
   - Show console logs of agent analysis
   - Demonstrate position updates as prices change

## 🚀 What's Working

✅ All 4 agents thinking consistently
✅ Agent decisions captured with full reasoning
✅ Position tracking with entry/exit prices
✅ P&L calculations displayed live
✅ Consensus mechanism visible
✅ Risk Guardian veto shown
✅ Market regime detection working
✅ Dashboard panels auto-update on refresh

## 📈 Next Steps (For Future Enhancement)

- [ ] Add position exit reasons (SL/TP/Time-based)
- [ ] Show agent performance vs actual prices
- [ ] Add trade history with P&L per trade
- [ ] Real-time WebSocket updates (no refresh needed)
- [ ] Agent neural network confidence heatmaps
- [ ] Risk metrics breakdown per position
- [ ] Compliance check status per trade

---

**Status:** ✅ LIVE AND READY FOR VIDEO RECORDING

Your dashboard now shows **real-time AI agent thinking** with complete reasoning and **live position tracking** with P&L. Perfect for demonstrating autonomous trading in action!
