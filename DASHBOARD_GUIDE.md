# 🎯 NEXUS Dashboard - Testing Hub

## Overview

A comprehensive HTML/JavaScript dashboard for visualizing NEXUS Trading AI bot performance, similar to MetaTrader5, with Prism's signature color palette.

**Features:**
- 📊 Real-time market data (BTC/USD price, volume, 24h change)
- 🤖 Agent performance tracking (weight, trades, PnL, win rate)
- 📈 Price chart (1H candles with Cyan theme)
- 💰 Equity curve with drawdown visualization
- 😊 Sentiment analysis (Fear & Greed Index, trending, community, momentum)
- ⚠️ Risk metrics (risk score, max drawdown, Sharpe ratio, volatility)
- 🎨 MetaTrader5-style dark theme with Prism colors

---

## Quick Start

### Option 1: Static HTML Dashboard (No Backend)

Simply open the dashboard directly in your browser:

```bash
# macOS
open dashboard.html

# Linux
firefox dashboard.html

# Windows
start dashboard.html
```

**Features with static version:**
- ✅ Full UI layout
- ✅ Mock market data (CoinGecko integration)
- ✅ Agent performance from `nexus_weights.json`
- ✅ Simulated equity curve
- ✅ Real Fear & Greed Index from Alternative.me
- ⚠️ Limited to 15-second refresh of market data

---

### Option 2: Flask API Server (Recommended - Full Real-time)

**Install dependencies:**
```bash
pip install flask flask-cors
```

**Start the server:**
```bash
python3 dashboard_server.py
```

**Access the dashboard:**
Open http://localhost:5000 in your browser

**API Endpoints Available:**
```
GET  /                    → Dashboard HTML
GET  /api/market          → Real-time market data from PRISM
GET  /api/agents          → Agent weights & performance
GET  /api/sentiment       → Sentiment analysis (4 sources)
GET  /api/positions       → Current open positions
GET  /api/equity          → Equity curve data
GET  /api/risk            → Risk metrics from PRISM
GET  /api/performance     → Aggregated performance stats
GET  /api/health          → Server health check
```

---

## Dashboard Panels

### 1. Market Overview
- **BTC Price** → Current price with 24h change %
- **24h Volume** → Trading volume in billions
- **Market Regime** → Trending/Ranging/Volatile
- **Fear & Greed** → Index value (0-100)

### 2. Price Chart
- **1H Candle Chart** → 24-hour price action
- **Cyan colored** → Prism theme
- **Interactive** → Hover for details

### 3. Agent Performance
- **Individual agents:**
  - Name, Weight, Trades, Wins, PnL
  - Weight progression bar
- **Aggregated metrics:**
  - Total Trades
  - Win Rate %
  - Total PnL $
  - Avg Return per trade

**Agents tracked:**
- Momentum (Trend following)
- Sentiment (Contrarian signals)
- Risk Guardian (Position sizing & veto)
- Mean Reversion (Oversold/overbought)

### 4. Risk Metrics Panel
- **Risk Score** → 0-100 (green/orange/red)
- **Max Drawdown** → Largest peak-to-trough decline
- **Sharpe Ratio** → Risk-adjusted returns
- **Volatility** → 30-day annualized
- **Open Positions** → Current trade count

### 5. Sentiment Analysis
- **Fear & Greed Index** (40% weight)
  - 0-25: Extreme Fear → Buy signal
  - 50: Neutral
  - 75-100: Extreme Greed → Sell signal
  
- **Trending** (20% weight)
  - BTC in top 3 trending = overheated
  
- **Community Votes** (25% weight)
  - Up% vs Down% sentiment
  
- **Momentum** (15% weight)
  - 24h price change as proxy

### 6. Equity Curve
- **Green line:** Account equity over time
- **Red line:** Maximum drawdown %
- **Dual axis** → Both metrics visible

---

## Color Scheme (Prism)

```
Dark Background:     #0A0E27 (--prism-dark)
Surface Layer:       #141829 (--prism-dark-secondary)
Primary Blue:        #2E5BFF (--prism-blue)
Accent Cyan:         #00D9FF (--prism-cyan)
Bullish Green:       #00FF88
Bearish Red:         #FF3333
Text Primary:        #FFFFFF
Text Secondary:      #8B92A9 (--prism-gray)
Borders:             #2A3544
```

---

## Data Sources

### Real-time Market Data
- **CoinGecko API** → BTC price, 24h volume, market cap
- **PRISM API** → Signals (1h, 4h), risk metrics, price feeds
- **Kraken CLI** → Live Kraken market data

### Sentiment Sources
1. **Alternative.me** → Fear & Greed Index (40%)
2. **CoinGecko Trending** → Top 7 trending coins (20%)
3. **CoinGecko Community** → Community sentiment votes (25%)
4. **Messari** → 24h price momentum (15%)

### Bot Performance
- `nexus_weights.json` → Agent weights, trades, PnL
- `nexus_positions.json` → Current open positions
- `nexus_equity_curve.json` → Daily equity snapshots

---

## Customization

### Change Refresh Rate
Edit `dashboard.html` line ~680:
```javascript
const CONFIG = {
    UPDATE_INTERVAL: 15000, // milliseconds (default: 15 seconds)
};
```

### Add New Agent
1. Update `agents/` directory with new agent class
2. Dashboard auto-discovers from `nexus_weights.json`

### Modify Color Scheme
Edit CSS variables in `dashboard.html` around line 30:
```css
:root {
    --prism-dark: #0A0E27;
    --prism-cyan: #00D9FF;
    --bullish: #00FF88;
    --bearish: #FF3333;
    /* ... etc */
}
```

---

## Real-time Monitoring

### During Training Cycle
While running `python3 main.py --dry-run -v`, the dashboard shows:
- **Live BTC price** updates every 15 seconds
- **Agent votes** as they're cast
- **Market regime** detection (TRENDING/RANGING/VOLATILE)
- **Risk veto** when risk_score >= 75
- **Weight updates** when positions close
- **Sentiment shift** in real-time from 4 free APIs

### Expected Patterns
```
Initial Run:
  - All agent weights ≈ 1.0
  - 0 trades (first cycle)
  
After 5 trades:
  - Weights start diverging
  - Profitable agents > 1.0
  - Losing agents < 1.0
  
After 24+ hours:
  - Clear agent specialization
  - Winner weight: 1.1-1.3
  - Loser weight: 0.7-0.9
```

---

## Troubleshooting

### Dashboard won't load
- Check browser console (F12) for errors
- Ensure `dashboard.html` is in same directory
- Try with `-disable-web-security` flag on Chrome

### No market data showing
- Check internet connection
- CoinGecko API rate limit: 10-50 calls/min (free tier)
- PRISM API key valid in `config.py`

### Agent data shows zeros
- Check `nexus_weights.json` exists
- Run one training cycle first with `python3 main.py --dry-run -v`
- Allow 5+ minutes for trades to register

### Charts not updating
- Enable JavaScript in browser
- Check browser console for Chart.js errors
- Flask server running on port 5000?

---

## Integration with Training Loop

The dashboard auto-syncs with the training system:

1. **Training runs:** `python3 main.py --dry-run -v`
2. **Updates weights:** Writes to `nexus_weights.json`
3. **Dashboard sees updates:** Next 15-second refresh cycle
4. **Visualizes real-time:** Agent cards, metrics update live

**No manual sync needed** — just open dashboard and watch training happen!

---

## Performance Tips

- **Reduce refresh rate** if CPU usage high: `UPDATE_INTERVAL: 30000`
- **Disable chart animations** for faster rendering
- **Close unused browser tabs** to free memory
- **Use Chrome/Brave** for better JavaScript performance

---

## Next Steps

1. ✅ Open `dashboard.html` to see the UI
2. ✅ Run `python3 main.py --dry-run -v` in another terminal
3. ✅ Watch dashboard update as trades execute
4. ✅ Monitor agent weight divergence over time
5. ✅ Use for validation during 24-48 hour training runs

---

**Dashboard Version:** 1.0  
**Last Updated:** April 11, 2026  
**Theme:** Prism Analytics | MetaTrader5-style  
**Status:** ✅ Production Ready

