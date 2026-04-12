# NEXUS PnL Capture Issue — Root Cause Analysis

## Problem Summary
The model is:
1. ❌ Not executing trades (or executing in dry-run only)
2. ❌ Not capturing PnL properly (equity curve shows alternating negative values)
3. ❌ Portfolio value calculation is inconsistent (cash shows 0 then 10000, alternating)

---

## Root Causes Identified

### Issue 1: DRY-RUN Mode Blocking Trades
**Location**: `main.py` line 647
```python
dry_run = args.dry_run or not args.live
```

**Problem**: 
- By default, `dry_run=True` unless `--live` flag is explicitly passed
- Running `python3 main.py --live` is required for actual trade execution
- Without `--live`, trades are only simulated, positions opened in memory but NOT executed on Kraken
- **Result**: No real positions → No real PnL → Equity curve stays stale

**Evidence**:
- Equity curve shows identical values repeating: `equity: 10000.0` with `realised_pnl: 0`
- Then suddenly shows `-5.067490644775754` when positions ARE opening but cash becomes 0
- This indicates the system is switching between open and closed positions in simulation

---

### Issue 2: Portfolio Value Calculation Bug
**Location**: `execution/positions.py` line 235
```python
def portfolio_equity_curve_add(self, cash: float, current_price: float, timestamp: int):
    unrealised = self.get_total_unrealised_pnl(current_price)
    realised = self.get_total_realised_pnl()
    total_equity = cash + unrealised + realised
```

**Problem**:
- When a position is OPEN: `cash=0, unrealised_pnl=-5.07, realised_pnl=-5.07`
  - Result: `equity = 0 + (-5.07) + (-5.07) = -10.14` ❌ **NEGATIVE equity is wrong**
  
- When position is CLOSED: `cash=10000, unrealised_pnl=0, realised_pnl=-5.07`
  - Result: `equity = 10000 + 0 + (-5.07) = 9994.93` ✓ Correct

**The alternating pattern in `nexus_equity_curve.json`:**
```json
{
  "timestamp": 1775990092,
  "equity": -5.067490644775754,    ← Open position: WRONG (negative)
  "cash": 0.0,
  "unrealised_pnl": 0.0,
  "realised_pnl": -5.067490644775754
},
{
  "timestamp": 1775990258,
  "equity": 9994.932509355223,     ← Closed position: CORRECT
  "cash": 10000.0,
  "unrealised_pnl": 0.0,
  "realised_pnl": -5.067490644775754
}
```

**Root Cause**: The `cash` value passed to `portfolio_equity_curve_add()` is **WRONG** when positions are open.

**Location**: `execution/kraken.py` line 142
```python
def portfolio_summary(self) -> Tuple[float, float]:
    # Extract BTC balance
    btc_balance = float(btc_balance_str)
    
    # Calculate BTC position value using current ticker price
    btc_position_usd = 0.0
    if btc_balance > 0:
        btc_price = self.get_ticker_price()  # <-- WHERE IS THIS METHOD?
        if btc_price:
            btc_position_usd = btc_balance * btc_price
    
    # ...missing: portfolio_value = usd_balance + btc_position_usd
    # ...missing: cash_usd = portfolio_value - open_position
```

**The method `get_ticker_price()` is called but NOT defined** in `KrakenClient`! This causes:
- `btc_position_usd` to remain 0 (price fetch fails silently)
- `portfolio_value` calculation incomplete
- `cash_usd` becomes incorrect (see line 154-156)

---

### Issue 3: Incomplete Kraken Portfolio Summary
**Location**: `execution/kraken.py` lines 140-160
```python
def portfolio_summary(self) -> Tuple[float, float]:
    """
    Returns: (portfolio_value_usd, open_position_usd)
    """
    # ... balance data extracted ...
    
    # INCOMPLETE: Missing return statement or incorrect calculation
    # Currently returns (0.0, 0.0) if BTC price fetch fails
```

**Evidence** from `main.py` line 428-433:
```python
# Fetch portfolio from Kraken (required)
portfolio_value, open_position = self.kraken.portfolio_summary()

# Calculate available cash
cash_usd = portfolio_value - open_position
```

If `portfolio_summary()` returns `(0.0, 0.0)`:
- `portfolio_value_usd = 0.0`
- `cash_usd = 0.0 - 0.0 = 0.0`
- Then in `portfolio_equity_curve_add()`: equity calculation becomes all realised PnL only

---

### Issue 4: Missing Position Reconciliation
**Location**: `main.py` line 428-429

**Problem**:
- System creates positions in `PositionManager` (in-memory JSON file)
- System creates orders via Kraken CLI
- **But**: There's no reconciliation between:
  - Positions opened by `position_manager.open_position()`
  - Actual Kraken account positions via `kraken_client.portfolio_summary()`

**Result**:
- If a trade executes on Kraken but position manager crashes, position is "orphaned"
- If position manager opens a position but Kraken CLI fails, system records PnL on ghost position
- **No trust**: The system doesn't verify orders were actually filled

---

## Quick Diagnosis

Run this to verify the issues:

```bash
# Check if portfolio_summary is working
python3 -c "
from execution.kraken import KrakenClient
k = KrakenClient()
portfolio_value, open_pos = k.portfolio_summary()
print(f'Portfolio: {portfolio_value}, Open Position: {open_pos}')
"

# Check what's in positions.json
cat nexus_positions.json | jq 'length'

# Check equity curve anomalies
cat nexus_equity_curve.json | tail -5 | jq '.[] | {equity, cash, status: (.realised_pnl)}'
```

---

## Why No Trades Are Taking Place

1. **Most likely**: Running without `--live` flag
   - Command: `python3 main.py --live --verbose`
   - NOT just: `python3 main.py`

2. **If --live is used but still no trades**:
   - Consensus votes might be failing (check `HOLD` logs)
   - Confidence threshold too high (config: `CONFIDENCE_THRESHOLD = 0.20`)
   - Compliance checks blocking trades (check for `[yellow]Trade blocked by compliance[/yellow]` messages)

3. **If trades execute but PnL shows wrong**:
   - Portfolio summary returning wrong values
   - Position not being closed (check `check_exits()` logic)
   - Cash calculation broken

---

## Fixes Required (Priority Order)

### Priority 1: Fix `portfolio_summary()` Kraken Integration
**File**: `execution/kraken.py` (lines 140-160)
- Implement missing `get_ticker_price()` method
- Fix portfolio value calculation
- Return correct cash available

### Priority 2: Fix Equity Curve Calculation
**File**: `execution/positions.py` (lines 225-250)
- Ensure `portfolio_equity_curve_add()` receives correct `cash` value
- Add validation: equity should never be negative (portfolio value floor = cash at minimum)
- Log when values are anomalous

### Priority 3: Add Position Reconciliation
**Files**: `main.py`, `execution/kraken.py`
- After `market_buy()` / `market_sell()`, verify Kraken returned filled order
- Compare position manager state with Kraken account state
- Log reconciliation failures

### Priority 4: Ensure --live Flag Behavior
**File**: `main.py` (lines 647, 593-600)
- Verify `dry_run` flag is respected
- Add logging when entering dry-run vs live mode
- Warn user if running in dry-run by default

---

## Expected Behavior After Fixes

1. Run: `python3 main.py --live --verbose`
2. Logs should show: `[bold red]Running in LIVE mode (real orders enabled)[/bold red]`
3. Equity curve should show:
   - Initial: `{timestamp, equity: 10000, cash: 10000, realised_pnl: 0}`
   - After trade open: `{timestamp, equity: 10000, cash: 9950, unrealised_pnl: ±50}`
   - After trade close: `{timestamp, equity: 10020, cash: 10000, realised_pnl: 20}`
   - **Never negative equity** 👍

---

## Testing Plan

```bash
# 1. Test portfolio_summary
python3 main.py --ping

# 2. Start live trading with verbose logging
python3 main.py --live --verbose 2>&1 | tee nexus_debug.log

# 3. In another terminal, monitor positions
watch -n 5 'cat nexus_positions.json | jq ".[] | select(.status==\"open\") | {trade_id, direction, entry_price, status}"'

# 4. Monitor equity curve
watch -n 5 'tail -1 nexus_equity_curve.json | jq "."'

# 5. After first trade closes, verify PnL
cat nexus_positions.json | jq '.[] | select(.status=="closed") | {trade_id, pnl_usd, pnl_pct}'
```

