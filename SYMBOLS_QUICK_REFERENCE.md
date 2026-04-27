# 🎯 QUICK REFERENCE — ALL SYMBOLS VISIBLE

## Status: ✅ ALL 16 SYMBOLS VISIBLE

---

## All Available Symbols (16 Total)

```
ACTIVE (14)                          INACTIVE (2)
══════════════════════════════════   ═══════════════════════
✅ BTC    Bitcoin         major       ⚪ PEPE   Pepe         meme
✅ ETH    Ethereum        major       ⚪ FLOKI  Floki        meme
✅ SOL    Solana          altcoin
✅ ADA    Cardano         altcoin
✅ POLKA  Polkadot        altcoin
✅ AVAX   Avalanche       altcoin
✅ MATIC  Polygon         altcoin
✅ UNI    Uniswap         defi
✅ AAVE   Aave            defi
✅ LINK   Chainlink       defi
✅ DOGE   Dogecoin        meme
✅ SHIB   Shiba Inu       meme
✅ ARB    Arbitrum        layer2
✅ OP     Optimism        layer2
```

---

## Where to View Each Symbol

### 1️⃣ Streamlit Dashboard
- **Command**: `streamlit run streamlit_app.py`
- **URL**: `http://localhost:8501`
- **Location**: Left sidebar → "Currencies" tab
- **Symbols Visible**: All 16 ✅
- **Features**: Filter by category, view prices, charts, signals

### 2️⃣ REST API
- **Command**: `python3 dashboard_server.py`
- **Base URL**: `http://localhost:3000`
- **Endpoint**: `/api/market-overview`
- **Symbols Returned**: All 16 ✅

### 3️⃣ HTML Dashboard
- **URL**: `http://localhost:3000`
- **Location**: Cryptocurrency section
- **Symbols Visible**: All 16 ✅
- **Features**: Live prices, status indicators

---

## API Endpoints (All Symbols)

### Get All Symbols
```bash
curl http://localhost:3000/api/market-overview
```
Returns: All 16 symbols with prices, volume, 24h change

### Get Individual Price
```bash
curl http://localhost:3000/api/crypto/BTC/price
curl http://localhost:3000/api/crypto/ETH/price
curl http://localhost:3000/api/crypto/SOL/price
# Works for all 16 symbols
```

### Get Trading Signals
```bash
curl http://localhost:3000/api/crypto/BTC/signals?timeframe=1h
curl http://localhost:3000/api/crypto/ETH/signals?timeframe=4h
# Works for all 16 symbols with 1h, 4h, 1d timeframes
```

---

## Data Sources

- **CoinGecko**: Historical data & market info (all 16 symbols)
- **Binance**: Live prices & OHLCV (all 16 symbols)
- **Update Frequency**: Every 30 seconds

---

## Configuration

**File**: `config.py`

```python
SUPPORTED_SYMBOLS = {
    "BTC": {"name": "Bitcoin", "category": "major", "active": True},
    "ETH": {"name": "Ethereum", "category": "major", "active": True},
    # ... all 16 symbols with metadata
}

WATCH_SYMBOLS = ["ETH", "SOL", "DOGE"]  # For agent analysis
```

---

## Verification

**Run Test**:
```bash
python3 verify_all_symbols_visible.py
```

**Output**: ✅ All 16 symbols confirmed visible

---

## Quick Test

**See all symbols in API**:
```bash
curl http://localhost:3000/api/market-overview | jq '.count'
# Output: 16
```

**See specific symbol**:
```bash
curl http://localhost:3000/api/crypto/ARB/price
curl http://localhost:3000/api/crypto/OP/price
```

---

## Categories

- **MAJOR** (2): BTC, ETH
- **ALTCOIN** (5): SOL, ADA, POLKA, AVAX, MATIC
- **DEFI** (3): UNI, AAVE, LINK
- **MEME** (4): DOGE, SHIB, PEPE, FLOKI
- **LAYER2** (2): ARB, OP

---

## Add New Symbol

1. Edit `config.py`:
   ```python
   SUPPORTED_SYMBOLS["NEW"] = {"name": "New", "category": "cat", "active": True}
   ```

2. Edit `data/free_market.py`:
   ```python
   COINGECKO_IDS["NEW"] = "id"
   BINANCE_PAIRS["NEW"] = "NEWUSDT"
   ```

3. Symbol automatically appears everywhere! ✅

---

## Summary

| Metric | Value |
|--------|-------|
| Total Symbols | 16 |
| Active | 14 |
| Visible in Streamlit | ✅ All 16 |
| Visible in REST API | ✅ All 16 |
| Visible in HTML Dashboard | ✅ All 16 |
| Data Coverage | ✅ 100% |

**Status: ✅ COMPLETE — ALL SYMBOLS VISIBLE**

