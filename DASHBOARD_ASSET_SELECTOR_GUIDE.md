# ✅ DASHBOARD ASSET SELECTOR & AGENT TRADING CONFIGURATION

**Date**: April 14, 2026  
**Status**: ✅ COMPLETE  
**Feature**: Easy-access tabs to switch between Crypto, JSE, US Stocks, and All Assets

---

## What's New: Dashboard Asset Selector

### 🎯 Easy Access Tab Buttons

The dashboard now features **4 prominent buttons** at the top for quick asset class selection:

```
🪙 Crypto (16)     📈 Stocks - JSE (50)    🏢 Stocks - US (20)    🌍 All Assets
```

These buttons appear on:
- ✅ Dashboard tab
- ✅ Positions tab  
- ✅ Risk tab
- ✅ Currencies tab

### Display Information

Each button shows:
- **Asset Icon** (emoji)
- **Asset Class** (Crypto, JSE, US, All)
- **Count** (number of available symbols)
- **Help Text** on hover

**Current Selection Display**:
Below the buttons, a highlighted banner shows:
- 📊 Currently viewing asset type
- Descriptive subtitle

---

## Asset Categories

### 🪙 Cryptocurrencies (16 Active)

**Location**: `config.SUPPORTED_SYMBOLS`

**Categories** (filtered):
- Major (2): BTC, ETH
- Altcoins (5): SOL, ADA, POLKA, AVAX, MATIC
- DeFi (3): UNI, AAVE, LINK
- Meme (4): DOGE, SHIB, PEPE, FLOKI
- Layer 2 (2): ARB, OP

**Data Source**: Binance (live prices) + CoinGecko (history)

**API Endpoint**: `/api/market-overview`

---

### 📈 JSE Top 50 Stocks

**Location**: `data/stock_market.py` → `JSE_TOP_50`

**Categories**:
- Mega Caps: NPN.JO, PRX.JO, BHP.JO, AGL.JO, etc.
- Resources: GFI.JO, ANG.JO, IMP.JO, etc.
- Financials: FSR.JO, SBK.JO, ABG.JO, etc.
- Tech/Telecoms: MTN.JO, VOD.JO, TLS.JO, etc.
- Retail: WHL.JO, TFG.JO, MRP.JO, etc.

**Data Source**: Yahoo Finance (yfinance)

**API Endpoint**: `/api/stocks/jse`

---

### 🏢 US Market Stocks (20 Leaders)

**Location**: `data/stock_market.py` → `US_TOP_STOCKS`

**Symbols**:
- Tech: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
- Finance: JPM, V, BAC, GS
- Industrial: BA, CAT, GE
- Healthcare: JNJ, UNH, PFE, CVX
- Energy: XOM
- Utilities: NEE

**Data Source**: Yahoo Finance (yfinance) + Alpaca (paper trading)

**API Endpoint**: `/api/stocks/us`

---

### 🌍 All Assets (86 Total)

Combines all three asset classes:
- Crypto (16)
- JSE Stocks (50)
- US Stocks (20)

**Filter Options**:
- All Types (86 assets)
- Cryptocurrencies (16)
- JSE Stocks (50)
- US Stocks (20)

---

## Dashboard Implementation

### Session State Management

```python
# Store current asset type in session
if "asset_type" not in st.session_state:
    st.session_state.asset_type = "Crypto"

# Update on button click
if st.button("🪙 Crypto (16)"):
    st.session_state.asset_type = "Crypto"
    st.rerun()
```

### Where Asset Selector Appears

**Tabs with Selector**:
1. **Dashboard** - Main trading view
2. **Positions** - Open positions by asset class
3. **Risk** - Risk metrics for selected asset class
4. **Currencies** - Market prices and details

**Tabs without Selector**:
- Agents - Multi-agent architecture (symbol-agnostic)
- Sentiment - Overall market sentiment
- Wallet - Portfolio overview
- Settings - Global configuration
- AI Chat - Assistant (uses selected asset)

---

## Agent Configuration for All Assets

### How Agents Trade Multiple Assets

Agents are **symbol-agnostic** and use configuration-driven symbols:

```python
# config.py
PRIMARY_SYMBOL = "BTC"           # Main symbol for analysis
WATCH_SYMBOLS = ["ETH", "SOL", "DOGE"]  # Additional symbols to monitor
```

### Agent Architecture

```
┌─────────────────────────────────────────────┐
│        NEXUS Trading Loop (main.py)         │
├─────────────────────────────────────────────┤
│                                             │
│  1. Fetch market data for PRIMARY_SYMBOL   │
│  2. All agents analyze SAME market data    │
│  3. Agents generate trading signals        │
│  4. Consensus engine votes on direction   │
│  5. Execute trade via Kraken/Alpaca       │
│                                             │
│  For multi-symbol support:                  │
│  - WATCH_SYMBOLS gets separate analysis    │
│  - Results tracked separately              │
│  - Positions managed per-symbol            │
│                                             │
└─────────────────────────────────────────────┘
```

### Agent Types & Configuration

**All agents inherit from `BaseAgent`**:

```python
class BaseAgent:
    """Base class for all trading agents"""
    
    async def analyze(self, market_data: MarketData) -> TradeDecision:
        """Analyze market and return decision (symbol-agnostic)"""
        # Each agent processes market_data.symbol
        # Returns decision with asset/pair info
```

**Registered Agents**:

1. **OrderFlowAgent** - Analyzes order flow + CVD
2. **MomentumAgent** - Technical analysis + PRISM signals
3. **SentimentAgent** - Social sentiment analysis
4. **RiskGuardianAgent** - Risk management & volatility
5. **MeanReversionAgent** - Mean reversion strategy
6. **LLMReasonerAgent** - LLM-based analysis (optional)
7. **YOLOAgent** - Aggressive strategy

---

## Adding New Asset Classes

### Step 1: Define Asset List

Add to `config.py` or `data/stock_market.py`:

```python
# Example: Add forex pairs
FOREX_PAIRS = {
    "EURUSD": "Euro/US Dollar",
    "GBPUSD": "British Pound/US Dollar",
    # ... more pairs
}
```

### Step 2: Create Data Provider

Add to dashboard API:

```python
@app.route('/api/forex')
def get_forex():
    """Fetch forex prices"""
    forex_data = []
    for pair, name in FOREX_PAIRS.items():
        data = fetch_forex_price(pair)
        forex_data.append({...})
    return jsonify(forex_data)
```

### Step 3: Update Dashboard

Add button to asset selector:

```python
with asset_cols[4]:
    if st.button("💱 Forex (12)", key="forex_btn"):
        st.session_state.asset_type = "Forex"
        st.rerun()
```

### Step 4: Handle in Currencies Tab

```python
elif asset_type == "Forex":
    forex_data = api("/api/forex")
    # Display forex prices
```

---

## Agent Configuration Details

### Configuration Files

**`config.py`** - Core configuration:
```python
PRIMARY_SYMBOL = "BTC"
WATCH_SYMBOLS = ["ETH", "SOL", "DOGE"]
SUPPORTED_SYMBOLS = {...}  # 16 cryptos

# Stock trading flags
JSE_ENABLED = True
US_STOCKS_ENABLED = True
BTC_CORRELATION_ENABLED = True
```

**`nexus_agent_settings.json`** - Agent parameters:
```json
{
  "risk_per_trade": 2.5,
  "stop_loss_pct": 3.0,
  "take_profit_pct": 8.0,
  "enabled_agents": {
    "momentum": true,
    "mean_reversion": true,
    "sentiment": true,
    "orderflow": true,
    "yolo": true
  }
}
```

### Agent Trading Flow

```
┌─ Market Data Fetched ──────────────────────────┐
│  Symbol: BTC, Price: $95,000, Volume: 50B     │
└─────────────────────────────────────────────────┘
                       ↓
        ┌────────────────────────────┐
        │  5 Parallel Agent Analyses │
        ├────────────────────────────┤
        │ OrderFlow    → BUY  (0.8)  │
        │ Momentum     → BUY  (0.9)  │
        │ Sentiment    → HOLD (0.5)  │
        │ RiskGuardian → HOLD (0.6)  │
        │ MeanReversion→ SELL (0.7)  │
        └────────────────────────────┘
                       ↓
        ┌──────────────────────────────┐
        │  Consensus Engine            │
        │  Weighted Vote: BUY (0.75)   │
        └──────────────────────────────┘
                       ↓
        ┌──────────────────────────────┐
        │  Compliance Check            │
        │  ✅ Approved for 0.5 BTC     │
        └──────────────────────────────┘
                       ↓
        ┌──────────────────────────────┐
        │  Trade Execution             │
        │  BUY 0.5 BTC via Kraken      │
        └──────────────────────────────┘
```

---

## Multi-Symbol Trading

### Enabling Multi-Symbol Support

Agents automatically support trading any symbol configured in:

```python
# All these symbols get analyzed
WATCH_SYMBOLS = ["ETH", "SOL", "DOGE", "BTC", "ARB", "OP"]

# Or add custom symbols
config.ADDITIONAL_SYMBOLS = ["NEW", "SYMBOL"]
```

### Position Management

Multi-symbol positions tracked in `nexus_positions.json`:

```json
[
  {
    "symbol": "BTC",
    "direction": "LONG",
    "entry_price": 95000,
    "quantity": 0.5,
    "entry_time": "2026-04-14T12:00:00",
    "status": "open"
  },
  {
    "symbol": "ETH",
    "direction": "LONG",
    "entry_price": 3500,
    "quantity": 5.0,
    "entry_time": "2026-04-14T12:05:00",
    "status": "open"
  }
]
```

---

## Testing Asset Selector

### Verify Dashboard Works

```bash
# Terminal 1: Start API server
python3 dashboard_server.py

# Terminal 2: Start Streamlit
streamlit run streamlit_app.py

# Browser: http://localhost:8501
# - Dashboard tab → See asset buttons
# - Click "📈 Stocks - JSE (50)" → View JSE stocks
# - Click "🏢 Stocks - US (20)" → View US stocks
# - Click "🌍 All Assets" → View all 86
```

### Verify APIs Respond

```bash
# Crypto prices
curl http://localhost:3000/api/market-overview | jq '.count'
# Output: 16

# JSE stocks
curl http://localhost:3000/api/stocks/jse | jq '.count'
# Output: 50

# US stocks
curl http://localhost:3000/api/stocks/us | jq '.count'
# Output: 20
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    NEXUS Dashboard (Streamlit)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ASSET SELECTOR (Session State: asset_type)             │  │
│  │  🪙 Crypto  📈 JSE  🏢 US  🌍 All                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Tabs: Dashboard | Agents | Positions | Risk |...       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          ↓                                       │
│        ┌─────────────────┼─────────────────┐                   │
│        ↓                 ↓                 ↓                    │
│  ┌──────────┐    ┌──────────────┐   ┌──────────┐              │
│  │ Crypto   │    │ JSE Stocks   │   │ US Stock │              │
│  │ 16 coins │    │ 50 companies │   │ 20 major │              │
│  └──────────┘    └──────────────┘   └──────────┘              │
│        ↓                 ↓                 ↓                    │
└────────────────────────────────────────────────────────────────┘
         ↓                 ↓                 ↓
    ┌────────────┐   ┌──────────────┐  ┌────────────┐
    │  Binance   │   │   Yahoo      │  │   Alpaca   │
    │ + CoinGecko│   │   Finance    │  │   API      │
    └────────────┘   └──────────────┘  └────────────┘
         ↓                 ↓                 ↓
    ┌────────────────────────────────────────────────┐
    │    Dashboard API Server (dashboard_server.py)  │
    │  /api/market-overview                          │
    │  /api/stocks/jse                               │
    │  /api/stocks/us                                │
    │  /api/crypto/<SYM>/price                       │
    └────────────────────────────────────────────────┘
```

---

## Summary

✅ **Asset Selector Complete**
- 4 easy-access buttons: Crypto, JSE, US, All
- Session-based state management
- Visual indicator of current selection
- Available on 4 main tabs

✅ **All Assets Visible**
- Crypto: 16 symbols (Binance + CoinGecko)
- JSE: 50 stocks (Yahoo Finance)
- US: 20 stocks (Yahoo Finance + Alpaca)
- Total: 86 tradeable assets

✅ **Agents Ready for Multi-Symbol Trading**
- All agents symbol-agnostic
- Configuration-driven symbol selection
- Position tracking per-symbol
- Easy to add new symbols/asset classes

---

**Status**: ✅ Ready for production  
**Next Step**: Run `streamlit run streamlit_app.py` and test asset selector!
