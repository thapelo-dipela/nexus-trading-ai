# NEXUS Profit-Driven Improvements Verification Checklist

## Pre-Launch Verification

### ✅ Code Compilation & Imports

- [ ] All new modules import without errors
  ```bash
  python -c "from execution.positions import PositionManager; print('✓ PositionManager')"
  python -c "from consensus.regime import RegimeDetector; print('✓ RegimeDetector')"
  python -c "from agents.mean_reversion import MeanReversionAgent; print('✓ MeanReversionAgent')"
  ```

- [ ] main.py imports correctly
  ```bash
  python -c "import main; print('✓ main.py')"
  ```

- [ ] No missing dependencies
  ```bash
  pip install -r requirements.txt  # Run to verify
  ```

### ✅ Configuration Files

- [ ] config.py has all new parameters
  - [ ] TAKE_PROFIT_PCT
  - [ ] STOP_LOSS_PCT
  - [ ] MAX_HOLD_TIME_MINUTES
  - [ ] POSITIONS_FILE
  - [ ] EQUITY_CURVE_FILE

- [ ] .env.example updated with new params
  - [ ] Set TAKE_PROFIT_PCT=5.0
  - [ ] Set STOP_LOSS_PCT=2.0
  - [ ] Set MAX_HOLD_TIME_MINUTES=1440

### ✅ Data Structures

- [ ] MarketData includes cash_usd field
  ```bash
  python -c "from agents.base import MarketData; m = MarketData.__dataclass_fields__; print('cash_usd' in m)"
  ```

- [ ] Position class has all required fields
  - [ ] trade_id, direction, entry_price, volume
  - [ ] exit_price, exit_timestamp, exit_reason
  - [ ] pnl_usd, pnl_pct, status

- [ ] RegimeDetector returns MarketRegime enum
  ```bash
  python -c "from consensus.regime import MarketRegime; print(MarketRegime.TRENDING.value)"
  ```

### ✅ Agent Registration

- [ ] MeanReversionAgent inherits from BaseAgent
  ```bash
  python -c "from agents.mean_reversion import MeanReversionAgent; from agents.base import BaseAgent; print(issubclass(MeanReversionAgent, BaseAgent))"
  ```

- [ ] MeanReversionAgent has analyze() method
  ```bash
  python -c "from agents.mean_reversion import MeanReversionAgent; m = MeanReversionAgent(); print(hasattr(m, 'analyze'))"
  ```

- [ ] All agents callable in trading loop
  - [ ] momentum agent
  - [ ] sentiment agent
  - [ ] risk_guardian agent
  - [ ] mean_reversion agent

---

## Connectivity Tests

### ✅ PRISM + Kraken

```bash
python main.py --ping
```

Expected results:
- [ ] PRISM /resolve/BTC ✓
- [ ] PRISM /crypto/BTC/price ✓ (shows price)
- [ ] PRISM /signals/BTC (1h) ✓ (shows direction + confidence)
- [ ] PRISM /signals/BTC (4h) ✓ (shows direction + confidence)
- [ ] PRISM /risk/BTC ✓ (shows risk_score)
- [ ] Kraken portfolio_summary ✓ (shows balance)

---

## Functional Tests (--dry-run mode)

### ✅ Position Manager

Run for 3 cycles (~15 minutes at 5min intervals):

```bash
python main.py --dry-run -v 2>&1 | tee test_run.log
```

Check logs for:

- [ ] **Cycle 1**: "Position opened: BUY X @ $PRICE"
  - Verify format: direction, volume, entry price

- [ ] **Cycle 2**: Market regime detected
  - [ ] "Market Regime: trending" or "ranging" or "high_volatility"
  - [ ] Regime weights printed: momentum, sentiment, risk_guardian, mean_reversion

- [ ] **Cycle 3**: Position still tracking
  - [ ] No errors in position management
  - [ ] Open positions logged in summary

### ✅ Regime Detection

Check for regime classification accuracy:

- [ ] In trending markets: momentum agent boosted (weight > 1.0)
- [ ] In ranging markets: mean_reversion agent boosted (weight > 1.0)
- [ ] In high volatility: risk_guardian weight > 1.5
- [ ] Weights adjust dynamically each cycle

### ✅ Agent Voting

Verify 4-agent voting:

- [ ] Momentum agent votes (confidence > 0.3)
- [ ] Sentiment agent votes (confidence > 0.3)
- [ ] Risk guardian votes (confidence > 0.3)
- [ ] Mean reversion agent votes (confidence > 0.3)
- [ ] All votes logged with regime multiplier

### ✅ Compliance Checks

Verify 10-point framework:

- [ ] All 10 checks logged (PASS or WARNING)
- [ ] No FAIL checks blocking trades (expected in normal operation)
- [ ] Real Sharpe ratio calculated (shown in Risk-Adjusted Return check)
- [ ] Position limits enforced

### ✅ Equity Curve Recording

After 3 cycles:

```bash
cat nexus_equity_curve.json | jq '.'
```

Expected structure:
```json
[
  {
    "timestamp": 1712800000,
    "equity": 50123.45,
    "cash": 45123.45,
    "unrealised_pnl": 5000.00,
    "realised_pnl": 0.00
  },
  ...
]
```

Verify:
- [ ] File created after first cycle
- [ ] Entries appended each cycle
- [ ] equity = cash + unrealised_pnl + realised_pnl
- [ ] Array grows monotonically

---

## Extended Tests (72+ hours dry-run)

### ✅ Position Lifecycle

Monitor for complete position lifecycle:

1. [ ] Position opened (STEP 1)
2. [ ] Position held through 2-3 cycles
3. [ ] Position closed (stop-loss, take-profit, or time-based)
4. [ ] PnL recorded (positive or negative)
5. [ ] Outcome pushed to logs (on-chain stub in dry-run)

### ✅ Feedback Loop

Verify agent learning:

```bash
cat nexus_weights.json | jq '.'
```

Expected changes:
- [ ] Agent weights INCREASE after winning trades
- [ ] Agent weights DECREASE after losing trades
- [ ] Momentum weight higher if trending regime more frequent
- [ ] Mean reversion weight higher if ranging regime more frequent

### ✅ Stop-Loss / Take-Profit

Verify exit logic:

- [ ] Position closed when unrealised PnL reaches +5% (take-profit)
- [ ] Position closed when unrealised PnL reaches -2% (stop-loss)
- [ ] Position closed after 1440 minutes (24 hours) if not already exited
- [ ] Exit reason logged correctly

### ✅ Equity Curve Growth

Verify portfolio equity evolution:

```bash
tail -10 nexus_equity_curve.json | jq '.[] | {timestamp, equity}'
```

Expected:
- [ ] Equity fluctuates (positions open/close)
- [ ] Trend generally upward (positive PnL on average)
- [ ] No extreme swings (drawdown < 5%)

---

## Agent-Specific Tests

### ✅ MeanReversion Agent

Check agent output in logs:

```bash
grep "mean_reversion" test_run.log
```

Expected:
- [ ] Agent votes BUY when RSI < 30 (oversold)
- [ ] Agent votes SELL when RSI > 70 (overbought)
- [ ] Agent votes HOLD in neutral RSI range
- [ ] Confidence scales with signal strength

### ✅ Regime Detector

Verify ADX calculation:

```bash
grep "Market Regime" test_run.log | head -20
```

Expected:
- [ ] "trending" when price has clear direction
- [ ] "ranging" when price oscillating
- [ ] "high_volatility" when ATR > 2%
- [ ] Classification changes appropriately

### ✅ Compliance Engine

Verify all 10 checks:

```bash
grep "✓" test_run.log | grep -E "(Position Size|Confidence|Concentration|Leverage|Volatility|Liquidity|Slippage|Risk-Adjusted|Drawdown|Trustless)"
```

Expected:
- [ ] All 10 checks logged as PASS (normal case)
- [ ] Occasional FAIL if edge cases hit (expected)

---

## Data Persistence Tests

### ✅ JSON Files Created

```bash
ls -lh nexus_*.json
```

Expected files:
- [ ] nexus_weights.json (agent learning)
- [ ] nexus_positions.json (position history)
- [ ] nexus_equity_curve.json (equity over time)
- [ ] hold_log.json (counterfactual tracking)

### ✅ File Content Validation

```bash
# Check weights format
python -c "import json; data = json.load(open('nexus_weights.json')); print(len(data), 'agents tracked')"

# Check positions format
python -c "import json; data = json.load(open('nexus_positions.json')); print(len(data), 'positions recorded')"

# Check equity curve format
python -c "import json; data = json.load(open('nexus_equity_curve.json')); print(len(data), 'equity snapshots')"
```

---

## Performance Benchmarks (After 72+ hours)

### ✅ Win Rate

```bash
# Count winning positions
python -c "
import json
with open('nexus_positions.json') as f:
    positions = [p for p in json.load(f) if p['status'] == 'closed']
    wins = len([p for p in positions if p['pnl_usd'] > 0])
    print(f'Win rate: {wins / len(positions) * 100:.1f}%')
"
```

Target: > 55%

### ✅ Sharpe Ratio

```bash
# Calculate Sharpe from equity curve
python -c "
import json
import math
with open('nexus_equity_curve.json') as f:
    data = json.load(f)
    equities = [d['equity'] for d in data]
    returns = [(equities[i] - equities[i-1]) / equities[i-1] for i in range(1, len(equities))]
    mean_ret = sum(returns) / len(returns)
    var = sum((r - mean_ret)**2 for r in returns) / len(returns)
    std = math.sqrt(var)
    sharpe = mean_ret / std if std > 0 else 0
    print(f'Sharpe ratio: {sharpe:.2f}')
"
```

Target: > 0.5 (goal: > 1.0)

### ✅ Maximum Drawdown

```bash
# Calculate max drawdown
python -c "
import json
with open('nexus_equity_curve.json') as f:
    data = json.load(f)
    equities = [d['equity'] for d in data]
    max_equity = max(equities)
    min_equity = min(equities)
    max_dd = (min_equity - max_equity) / max_equity * 100
    print(f'Max drawdown: {max_dd:.2f}%')
"
```

Target: < 5% (config limit)

### ✅ Agent Weight Evolution

```bash
# Check weight spread (indicates learning)
python -c "
import json
with open('nexus_weights.json') as f:
    agents = json.load(f)
    weights = [a['weight'] for a in agents]
    spread = max(weights) - min(weights)
    print(f'Weight spread (learning indicator): {spread:.2f}')
    print(f'Weight range: {min(weights):.2f} to {max(weights):.2f}')
"
```

Expected: Spread > 0.5 (indicates differentiation)

---

## Error Handling Tests

### ✅ Missing Market Data

Force test by stopping Kraken:
- [ ] System logs error without crashing
- [ ] Retries after 30 seconds
- [ ] Falls back gracefully

### ✅ Invalid Compliance Check

Create edge case (modify market_data temporarily):
- [ ] Compliance check handles gracefully
- [ ] Trade blocked with reason logged
- [ ] System continues to next cycle

### ✅ Position Manager Errors

Test position file corruption:
- [ ] System detects invalid JSON
- [ ] Resets to fresh state
- [ ] Resumes trading normally

---

## Final Sign-Off Checklist

Before going live, verify:

- [ ] All code compiles without errors
- [ ] All new modules import successfully
- [ ] Config parameters loaded correctly
- [ ] PRISM and Kraken connectivity confirmed
- [ ] 72+ hour dry-run completed successfully
- [ ] Win rate > 55%
- [ ] Sharpe ratio > 0.5
- [ ] Max drawdown < 5%
- [ ] All 4 agents voting correctly
- [ ] Regime detection working
- [ ] Position tracking complete lifecycle
- [ ] Feedback loop updating agent weights
- [ ] Equity curve accumulating correctly
- [ ] No unhandled exceptions in logs

---

## Live Trading Sign-Off

Once all checks above pass:

```bash
# Backup data before going live
cp nexus_*.json backups/

# Start live trading
python main.py

# Monitor first 24 hours closely
tail -f logs/nexus_trading.log
```

---

**Status**: 🟢 **Ready for Testing**

Execute this checklist before claiming production-ready status.

*NEXUS — Verified Profit-Driven Trading System*
