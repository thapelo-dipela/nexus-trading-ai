# 🎨 NEXUS Dashboard - Complete Testing Hub

## Overview

A professional-grade HTML/JavaScript/Python dashboard for monitoring NEXUS Trading AI bot performance in real-time. Combines MetaTrader5's interface design with Prism's distinctive color palette.

**Status:** ✅ Production Ready

---

## 📦 Files Created

```
dashboard.html          → Main dashboard (standalone, no backend required)
dashboard_server.py     → Flask API server for real-time data
hub.html               → Landing page & quick access hub
DASHBOARD_GUIDE.md     → Detailed user guide
requirements.txt       → Python dependencies (Flask added)
```

---

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

New packages added:
- `flask==3.0.0` → Web server
- `flask-cors==4.0.0` → Cross-origin requests

### Step 2: Verify Files

```bash
ls -la dashboard.html dashboard_server.py hub.html
```

---

## 📊 Three Ways to Use

### Option 1: Static Dashboard (No Backend) ⚡ Fastest

**Perfect for:** Quick viewing, no server setup needed

```bash
open dashboard.html
```

**Features:**
- ✅ Full UI layout
- ✅ Real-time CoinGecko market data
- ✅ Agent data from `nexus_weights.json`
- ✅ Simulated equity curve
- ✅ Real Fear & Greed Index
- ✅ 15-second auto-refresh

**Limitations:**
- No live PRISM data
- Agent data only updates when file changes

---

### Option 2: Flask Server (Recommended) 🔥 Full Featured

**Perfect for:** Extended monitoring, live training sessions

```bash
# Terminal 1: Start API server
python3 dashboard_server.py

# Terminal 2: Start training loop
python3 main.py --dry-run -v

# Browser: Open dashboard
open http://localhost:5000
```

**Features:**
- ✅ Everything from Option 1 PLUS:
- ✅ Live PRISM API integration
- ✅ Real risk metrics
- ✅ Live market signals
- ✅ RESTful API for custom integrations
- ✅ 8 API endpoints for data access

---

### Option 3: Hub Landing Page 🎯 Navigation Center

**Perfect for:** Project overview, quick access to tools

```bash
open hub.html
```

**Features:**
- 🎯 Quick links to all tools
- 📚 Documentation access
- ⚡ Command shortcuts
- 🔧 Configuration management
- 📊 System status overview

---

## 🎮 Dashboard Features

### Real-time Market Data
- **BTC/USD Price** → Live from CoinGecko
- **24h Volume** → Trading volume in billions
- **24h Change %** → Bullish/bearish color coded
- **Market Regime** → Trending/Ranging/Volatile detection
- **Fear & Greed** → Index (0-100)

### Agent Performance Tracking
- **Individual Agent Cards:**
  - Agent name (momentum, sentiment, risk_guardian, mean_reversion)
  - Current weight (1.0 = baseline, >1.0 = profitable, <1.0 = unprofitable)
  - Trades closed count
  - Wins vs losses
  - Total PnL ($)
  - Weight progression bar

- **Aggregated Metrics:**
  - Total trades across all agents
  - Win rate %
  - Total PnL $
  - Average return per trade

### Price Chart
- **1H Candles** → 24-hour price action
- **Cyan colored** → Prism theme
- **Interactive** → Hover for exact values
- **Responsive** → Auto-scales to data

### Equity Curve
- **Green line** → Account equity over time
- **Red line** → Maximum drawdown %
- **Dual axis** → Both metrics on same chart
- **Daily resolution** → Equity snapshots

### Sentiment Analysis (4 Sources)
1. **Fear & Greed Index** (40% weight)
   - Alternative.me API
   - 0-25: Extreme fear (buy signal)
   - 50: Neutral
   - 75-100: Extreme greed (sell signal)

2. **CoinGecko Trending** (20% weight)
   - Top 7 trending coins
   - BTC #1-3 = overheated market

3. **Community Votes** (25% weight)
   - Direct crowd sentiment
   - Up% vs Down% comparison

4. **Messari Momentum** (15% weight)
   - 24h price change
   - Momentum as proxy

### Risk Metrics
- **Risk Score** → 0-100 (safe/warning/danger)
- **Max Drawdown** → Largest peak-to-trough decline
- **Sharpe Ratio** → Risk-adjusted returns
- **Volatility** → 30-day annualized
- **Open Positions** → Current trade count

---

## 🎨 Color Scheme (Prism)

Perfect for intuitive signal recognition:

```
Dark Background:      #0A0E27
Surface Layer:        #141829
Primary Blue:         #2E5BFF  (action buttons)
Accent Cyan:          #00D9FF  (highlights)
Bullish Green:        #00FF88  (up signals)
Bearish Red:          #FF3333  (down signals)
Text Primary:         #FFFFFF
Text Secondary:       #8B92A9
Borders:              #2A3544
```

---

## 📡 API Endpoints (Flask Server)

When running `dashboard_server.py`, access these endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Dashboard HTML |
| `/api/market` | GET | Real-time market data |
| `/api/agents` | GET | Agent weights & performance |
| `/api/sentiment` | GET | Sentiment analysis (4 sources) |
| `/api/positions` | GET | Current open positions |
| `/api/equity` | GET | Equity curve data |
| `/api/risk` | GET | Risk metrics from PRISM |
| `/api/performance` | GET | Aggregated performance stats |
| `/api/health` | GET | Server health check |

**Example Usage:**

```bash
# Get live market data
curl http://localhost:5000/api/market | jq

# Get agent performance
curl http://localhost:5000/api/agents | jq '.agents[0]'

# Get sentiment blend
curl http://localhost:5000/api/sentiment | jq
```

---

## 🔄 Real-time Data Flow

```
Training Loop (main.py)
    ↓
    ├→ nexus_weights.json (agent updates)
    ├→ nexus_positions.json (trade updates)
    ├→ nexus_equity_curve.json (daily snapshots)
    ↓
Dashboard (dashboard.html)
    ↓
    ├→ Auto-fetches every 15s
    ├→ Parses JSON files
    ├→ Queries live APIs (CoinGecko, PRISM)
    ├→ Updates charts & metrics
    ↓
User sees live bot performance
```

---

## 📊 Training Cycle Integration

While running `python3 main.py --dry-run -v`, the dashboard shows:

```
Initial state:
  - All weights at 1.0
  - 0 trades

After cycle #1-5:
  - First trades close
  - Weights start adjusting
  - PnL appears in metrics

After 24 hours:
  - Clear agent specialization
  - Winner weight: 1.1-1.3
  - Loser weight: 0.7-0.9
  - Equity curve shows trend
  - Sentiment blend active
```

---

## 🛠️ Customization

### Change Refresh Rate

Edit `dashboard.html` around line 680:

```javascript
const CONFIG = {
    UPDATE_INTERVAL: 15000, // milliseconds
    // 5000 = every 5 seconds (intensive)
    // 30000 = every 30 seconds (light)
};
```

### Modify Color Scheme

Edit CSS variables in `dashboard.html` around line 30:

```css
:root {
    --prism-dark: #0A0E27;
    --prism-cyan: #00D9FF;
    --bullish: #00FF88;
    --bearish: #FF3333;
    /* ... customize as needed */
}
```

### Add Custom Charts

Add to `dashboard.html` JavaScript:

```javascript
// Create new chart
const myChart = new Chart(ctx, {
    type: 'line',
    data: { /* ... */ },
    options: { /* ... */ }
});
```

---

## 🔧 Troubleshooting

### Dashboard won't load
- ❌ File not found → Check `dashboard.html` in same directory
- ❌ JavaScript error → Check browser console (F12)
- ❌ CORS error → Start Flask server with `dashboard_server.py`

### No market data
- ❌ CoinGecko rate limit → Wait 1 minute, try again
- ❌ No internet → Check connection
- ❌ API down → Fallback to mock data active

### Charts not updating
- ❌ JavaScript disabled → Enable it
- ❌ Chart.js not loaded → Check CDN availability
- ❌ No data → Run training cycle first

### Agent data shows zeros
- ❌ `nexus_weights.json` not found → Run training cycle
- ❌ File permissions → Check read access
- ❌ File format → Verify JSON structure

### Flask server won't start
```bash
# Port already in use?
lsof -i :5000

# Kill process on port 5000
kill -9 <PID>

# Try different port (edit dashboard_server.py)
app.run(host='0.0.0.0', port=5001)
```

---

## 📈 Performance Tips

- **Reduce refresh rate** if CPU usage high
- **Disable chart animations** for faster rendering
- **Use Chrome/Brave** for better performance
- **Close unused tabs** to free memory
- **Run server on separate machine** for production

---

## 🔐 Security Notes

- Dashboard runs locally (no cloud upload)
- API key only in `config.py` (not sent to frontend)
- CORS enabled for `localhost:5000` only
- Consider firewall rules for remote access

---

## 📚 Related Documentation

- `DASHBOARD_GUIDE.md` → User guide with details
- `TRAINING_GUIDE.md` → Training system architecture
- `config.py` → All configuration options
- `main.py` → Training loop implementation

---

## ⚡ Quick Commands

```bash
# Open dashboard directly
open dashboard.html

# Start with API server (recommended)
python3 dashboard_server.py
# Then: open http://localhost:5000

# Open hub landing page
open hub.html

# Run training while monitoring
python3 main.py --dry-run -v

# Check connectivity
python3 main.py --ping

# Run tests
bash run_tests.sh

# Monitor training (in separate terminal)
python3 training_monitor.py
```

---

## 🎯 Next Steps

1. ✅ Open `hub.html` for overview
2. ✅ Open `dashboard.html` for static view
3. ✅ Run `python3 dashboard_server.py` for live data
4. ✅ Start training with `python3 main.py --dry-run -v`
5. ✅ Watch dashboard update in real-time
6. ✅ Monitor agent weight divergence over 24-48 hours

---

## 📝 Version History

**v1.0** (April 11, 2026)
- ✅ Complete HTML dashboard with MetaTrader5 UI
- ✅ Flask API server with 8 endpoints
- ✅ Real-time market data integration
- ✅ Agent performance tracking
- ✅ Sentiment analysis (4 sources)
- ✅ Risk metrics visualization
- ✅ Equity curve & drawdown chart
- ✅ Hub landing page
- ✅ Comprehensive documentation

---

**Dashboard Status:** 🟢 Production Ready

Ready to monitor your NEXUS bots in real-time! 🚀

