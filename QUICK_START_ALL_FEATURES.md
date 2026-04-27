# 🚀 Quick Start — All 4 Features Implemented

## ✅ Status: READY TO USE

All features requested are now implemented and ready:

1. ✅ **Currencies Tab** — View all 16 cryptocurrencies
2. ✅ **MetaMask Wallet** — Connect and manage assets  
3. ✅ **Multi-Coin Trading** — Support for all 16 cryptos
4. ✅ **Variable Leverage** — 2x to 20x per coin

---

## 🎯 Quick Test

### Step 1: Start Services
```bash
# Terminal 1: Start Dashboard API
python3 dashboard_server.py

# Terminal 2: Start Streamlit Dashboard
python3 -m streamlit run streamlit_app.py
```

### Step 2: View Currencies
1. Open http://localhost:8501
2. Click **"Currencies"** tab in sidebar
3. See table with all 16 cryptocurrencies
4. Filter by category or select individual crypto
5. View 1h/4h signals and charts

### Step 3: Connect MetaMask Wallet
1. Click **"Wallet"** tab in sidebar
2. Click **"Connect MetaMask Wallet"** button
3. See connected address and wallet balances
4. View portfolio breakdown (ETH, USDC, ARB, OP)

### Step 4: Test Multi-Coin Trading
```python
from execution.multi_symbol_trading import MultiSymbolPortfolio

portfolio = MultiSymbolPortfolio()

# Open positions for 16 cryptocurrencies
portfolio.open_position("BTC", "LONG", 84022.0, 0.01, leverage=10.0)
portfolio.open_position("ETH", "LONG", 2500.0, 1.0, leverage=6.67)
portfolio.open_position("DOGE", "LONG", 0.25, 10000.0, leverage=3.33)

# Get metrics
metrics = portfolio.get_portfolio_metrics({
    "BTC": 84500.0,
    "ETH": 2520.0,
    "DOGE": 0.26
})

print(f"Total PnL: ${metrics['total_unrealized_pnl']:+.2f}")
```

---

## 📊 Leverage Settings

| Coin | Margin Ratio | Leverage | Risk Level |
|------|------------|----------|-----------|
| BTC | 0.10 | 10x | Standard |
| ETH | 0.15 | 6.67x | Standard |
| SOL | 0.20 | 5x | Standard |
| DOGE | 0.30 | 3.33x | Conservative |
| PEPE | 0.50 | 2x | Very Conservative |

---

## 📁 Files Modified

| File | Type | Changes |
|------|------|---------|
| `config.py` | Modified | +30 lines (margin configs) |
| `streamlit_app.py` | Modified | +50 lines (MetaMask) + 120 lines (Wallet tab) |
| `execution/multi_symbol_trading.py` | NEW | 300+ lines (portfolio manager) |

---

## 🔧 Configuration

### Change Leverage
Edit `config.py`:
```python
SYMBOL_MARGIN_RATIOS = {
    "BTC": 0.05,   # 20x leverage (aggressive)
    "ETH": 0.1,    # 10x leverage
    "DOGE": 0.2,   # 5x leverage (less risky than 3.33x)
}
```

### Change Global Defaults
```python
DEFAULT_MARGIN_RATIO = 0.05    # 20x by default
MIN_MARGIN_RATIO = 0.02        # Allow up to 50x
MAX_MARGIN_RATIO = 1.0         # Never more than 1x max
```

---

## 📖 API Reference

### Get All Cryptocurrencies
```bash
curl http://localhost:3000/api/market-overview | jq '.currencies'
```

### Get Single Crypto Price
```bash
curl http://localhost:3000/api/crypto/ETH/price
```

### Get Trading Signals
```bash
curl http://localhost:3000/api/crypto/SOL/signals?timeframe=1h
```

---

## 🎨 Dashboard Features

**Currencies Tab**:
- 📊 Market price table
- 🔍 Category filter
- 📈 Interactive charts
- 🎯 Signal indicators

**Wallet Tab**:
- 🦊 MetaMask connect
- 💰 Asset display
- 🔄 Send/Approve
- 📋 Transaction history

---

## 🚀 Next Steps

1. **Test Streamlit UI** → Navigate to Currencies & Wallet tabs
2. **Test API** → curl endpoints to verify data
3. **Integrate with agents** → Import MultiSymbolPortfolio in main.py
4. **Deploy** → Run both services in production

---

**Everything is ready to go!** 🎉

