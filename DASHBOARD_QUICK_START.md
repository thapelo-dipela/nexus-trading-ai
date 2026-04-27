# 🚀 QUICK START — Dashboard Asset Selector

**Status**: ✅ Ready to use  
**Location**: Streamlit Dashboard (tabs: Dashboard, Positions, Risk, Currencies)

---

## How to Use

### 1. Start the Dashboard

```bash
streamlit run streamlit_app.py
```

Open: `http://localhost:8501`

### 2. Select Asset Class

Look for the 4 buttons at the top:

- 🪙 **Crypto (16)** → 16 cryptocurrencies
- 📈 **Stocks - JSE (50)** → South African stocks
- 🏢 **Stocks - US (20)** → US market stocks
- 🌍 **All Assets** → All 86 assets combined

Click any button to filter dashboard content.

### 3. View Current Selection

Below buttons: Highlighted banner showing:
- Current asset type
- Brief description
- Asset count

### 4. View Details

**In Currencies tab**:
- Market prices table
- Filter by category (if applicable)
- Select individual asset for detailed view
- Charts and signals

---

## Available Assets

| Asset Class | Count | Symbols | Source |
|-------------|-------|---------|--------|
| Crypto | 16 | BTC, ETH, SOL, ADA, POLKA, AVAX, MATIC, UNI, AAVE, LINK, DOGE, SHIB, ARB, OP, PEPE, FLOKI | Binance + CoinGecko |
| JSE Stocks | 50 | NPN.JO, PRX.JO, BHP.JO, AGL.JO, FSR.JO, SBK.JO, ABG.JO, NED.JO, ... | Yahoo Finance |
| US Stocks | 20 | AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, JPM, V, JNJ, ... | Yahoo Finance + Alpaca |
| **Total** | **86** | All of above | Multiple APIs |

---

## Features by Tab

### Dashboard Tab
- Asset selector at top
- Market overview for selected asset class
- Agent consensus voting
- Market signals
- Agent weights

### Positions Tab  
- View open trades filtered by asset class
- Position details and P&L
- Exit signals

### Risk Tab
- Risk metrics for selected asset class
- Volatility analysis
- Drawdown metrics

### Currencies Tab
- Full market view with filters
- Price updates (30-second refresh)
- Detailed view for individual assets
- Price charts
- Trading signals (1h, 4h)

### Other Tabs (No Asset Filter)
- **Agents** - Overall agent performance
- **Sentiment** - Market sentiment (all assets)
- **Wallet** - Portfolio overview
- **Settings** - Global config
- **AI Chat** - Assistant (uses selected asset)

---

## What Agents Trade

### Currently Configured

**Primary Symbol**: `BTC`
**Watch Symbols**: `ETH`, `SOL`, `DOGE`

### How to Add More

Edit `.env` or `config.py`:

```
PRIMARY_SYMBOL=BTC
WATCH_SYMBOLS=ETH,SOL,DOGE,ARB,OP
```

Agents automatically analyze all symbols!

### Agent Types

1. **OrderFlow** - CVD-based trading
2. **Momentum** - Technical + PRISM signals
3. **Sentiment** - Social sentiment
4. **RiskGuardian** - Risk management
5. **MeanReversion** - Mean reversion strategy
6. **LLMReasoner** - AI-powered analysis (optional)
7. **YOLO** - Aggressive strategy

All agents vote on each symbol separately.

---

## API Endpoints

### Get Asset Data

```bash
# All cryptos
curl http://localhost:3000/api/market-overview

# JSE stocks
curl http://localhost:3000/api/stocks/jse

# US stocks
curl http://localhost:3000/api/stocks/us

# Single crypto
curl http://localhost:3000/api/crypto/BTC/price

# Trading signals
curl http://localhost:3000/api/crypto/BTC/signals?timeframe=1h
```

---

## Configuration

### Main Files

- `config.py` - Core settings
- `.env` - Environment variables
- `nexus_agent_settings.json` - Agent parameters

### Key Settings

```
PRIMARY_SYMBOL=BTC           # Main trading symbol
WATCH_SYMBOLS=ETH,SOL,DOGE   # Additional symbols
JSE_ENABLED=true             # Enable JSE trading
US_STOCKS_ENABLED=true       # Enable US stock trading
```

---

## Troubleshooting

### Asset selector not showing?

Check you're on: Dashboard, Positions, Risk, or Currencies tab

### Data not loading?

```bash
# Check API is running
python3 dashboard_server.py

# Check for errors
curl http://localhost:3000/api/market-overview
```

### Stocks showing 0 price?

Ensure `yfinance` is installed:
```bash
pip install yfinance --break-system-packages
```

---

## Summary

✅ **4 asset buttons** for quick switching  
✅ **86 total assets** available  
✅ **All agents ready** for multi-symbol trading  
✅ **Easy to extend** with new assets  
✅ **Session-based** - selection persists during use  

**Ready to trade!** 🚀
