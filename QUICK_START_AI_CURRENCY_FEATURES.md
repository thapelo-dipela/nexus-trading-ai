# ⚡ Quick Start: AI Chat & Multi-Currency Features

## 🌍 Multi-Currency Feature

### HTML Dashboard
```bash
1. Open dashboard.html in browser
2. Click "Currencies" tab
3. Select desired currency from dropdown (15 options)
4. All prices update instantly
5. Exchange rate displays in the card
```

**Available Currencies**:
🇺🇸 USD, 🇿🇦 ZAR, 🇪🇺 EUR, 🇬🇧 GBP, 🇯🇵 JPY, 🇨🇳 CNY, 🇮🇳 INR, 🇦🇺 AUD, 🇨🇦 CAD, 🇸🇬 SGD, 🇭🇰 HKD, 🇲🇽 MXN, 🇧🇷 BRL, 🇨🇭 CHF, 🇰🇷 KRW

### Streamlit Dashboard
```bash
1. Open streamlit_app.py
2. Look at sidebar
3. Find "📊 Display Currency" selector
4. Choose your currency
5. All tabs automatically update
```

**How It Works**:
- Currency selection applies to ALL tabs
- Applies to Dashboard, Currencies, Risk, Positions tabs
- Persists during your session
- All 86 assets (crypto + JSE + US stocks) convert automatically

---

## 🤖 AI Chat Position Control

### Close a Position

**Via AI Chat**:
```
User: "close position 1"
NEXUS: "✅ Position 1 has been closed successfully!"
```

**Via Positions Tab**:
1. Go to "Positions" tab
2. Select position from dropdown under "Close Position" section
3. Click "🔴 Close Position" button
4. Success message appears

### Open/Reopen a Position

**Via AI Chat**:
```
User: "open position 1"
NEXUS: "✅ Position 1 has been reopened successfully!"
```

**Command Examples**:
- "close position 1" ✓
- "close trade 3" ✓
- "open position 1" ✓
- "reopen position 2" ✓

### Position Status

Positions now show status:
- **OPEN** - Active position (in "Open Positions" table)
- **CLOSED** - Closed position (in "Recent Closed Trades" table)

Each position also displays an ID for easy reference.

---

## 📊 Multi-Currency API Endpoints

### Get Prices in Any Currency
```bash
# Crypto in ZAR
curl "http://localhost:3000/api/market-overview?currency=ZAR"

# JSE stocks in USD
curl "http://localhost:3000/api/stocks/jse?currency=USD"

# US stocks in EUR
curl "http://localhost:3000/api/stocks/us?currency=EUR"
```

### Get Exchange Rate
```bash
curl "http://localhost:3000/api/exchange-rate?from=USD&to=ZAR"

Response:
{
  "rate": 16.43,
  "from": "USD",
  "to": "ZAR",
  "timestamp": "2026-04-14T12:00:00"
}
```

### Get Available Currencies
```bash
curl "http://localhost:3000/api/currencies"

Response includes all 15 currencies with names and symbols
```

---

## 🔄 Position Management API Endpoints

### Close Position
```bash
POST /api/positions/{position_id}/close

Response:
{
  "success": true,
  "message": "Position 1 closed successfully",
  "position_id": "1",
  "status": "closed"
}
```

### Open Position
```bash
POST /api/positions/{position_id}/open

Response:
{
  "success": true,
  "message": "Position 1 reopened successfully",
  "position_id": "1",
  "status": "open"
}
```

---

## 💡 Usage Scenarios

### Scenario 1: View All Assets in ZAR
1. Open Streamlit dashboard
2. Select "ZAR" from sidebar currency selector
3. All prices now display in South African Rand
4. Navigate between tabs - currency persists

### Scenario 2: Convert JSE Stock to USD
1. HTML Dashboard → Currencies tab
2. Click "📈 JSE (50)" asset button
3. Select "USD" from currency dropdown
4. All 50 JSE stocks now show in USD
5. See exchange rate: "1 ZAR = 0.0609 USD"

### Scenario 3: Close Trading Position via Chat
1. Open AI Chat tab
2. Type: "close position 1"
3. Get confirmation: "✅ Position 1 has been closed!"
4. Go to Positions tab
5. Verify: Position now shows as "CLOSED" in trade history

### Scenario 4: Emergency Position Close
1. Go to Positions tab
2. Find open position
3. Select from "Close Position" dropdown
4. Click "🔴 Close Position"
5. UI closes position immediately

---

## ⚙️ Technical Details

### Currency Conversion
- **Base Currencies**:
  - Crypto: USD
  - JSE: ZAR
  - US Stocks: USD
  
- **Exchange Rates**:
  - Fetched from ExchangeRate-API (real-time)
  - Cached for 60 minutes
  - Fallback hardcoded rates always available

### Position Storage
- Positions stored in `nexus_positions.json`
- Status persists on close/open
- Timestamps recorded for auditing
- Position ID required for management

### Supported Assets (86 Total)
- 16 Cryptocurrency assets
- 50 JSE stocks
- 20 US stocks
- All convertible to 15 currencies

---

## 🐛 Troubleshooting

**Q: Currency dropdown not showing values**
A: Ensure API is running. Check `/api/currencies` endpoint.

**Q: AI Chat not recognizing "close position" command**
A: Use exact format: "close position X" where X is a number.

**Q: Position not closing**
A: Verify position ID exists and is currently open, not closed.

**Q: Exchange rate not updating**
A: Check internet connection. Fallback rates used if API unavailable.

**Q: Currency resets on page refresh**
A: Re-select currency (it persists during session in HTML, across tabs in Streamlit).

---

## 📋 Files Modified

- `dashboard.html` - Added currency selector
- `streamlit_app.py` - Added currency sidebar, position management
- `dashboard_server.py` - Added close/open position endpoints

---

## ✅ Verification

To verify everything is working:

```bash
# 1. Start the API server
python3 dashboard_server.py

# 2. Test currency endpoint
curl "http://localhost:3000/api/market-overview?currency=ZAR"

# 3. Test position closing
curl -X POST "http://localhost:3000/api/positions/1/close"

# 4. Open HTML dashboard
open dashboard.html

# 5. Start Streamlit dashboard
streamlit run streamlit_app.py
```

---

## 🎯 Feature Summary

✅ **Multi-Currency Display**
- 15 currencies supported
- Real-time exchange rates
- HTML dashboard currency selector
- Streamlit sidebar selector
- All 86 assets convertible

✅ **Position Management**
- Close via AI Chat ("close position X")
- Close via UI button
- Reopen positions ("open position X")
- Position status tracking
- Persistent storage

✅ **User Experience**
- Instant currency switching
- Intuitive UI controls
- Clear confirmation messages
- Works across all dashboards

---

**Status**: ✅ READY FOR USE

All features tested and working. Start using now!

