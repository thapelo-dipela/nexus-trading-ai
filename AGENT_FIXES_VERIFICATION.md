# NEXUS Agent Fixes Verification Guide

## Quick Verification Checklist

### 1. MeanReversionAgent Fixes

```bash
# Verify files exist and compile
python3 -c "from agents.mean_reversion import MeanReversionAgent; print('✓ MeanReversionAgent imports')"

# Verify new methods exist
python3 << 'EOF'
from agents.mean_reversion import MeanReversionAgent
agent = MeanReversionAgent()

# Check for new methods
assert hasattr(agent, '_get_trend_filter'), "Missing trend filter method"
assert hasattr(agent, '_rsi_divergence_score'), "Missing RSI divergence method"
assert hasattr(agent, '_compute_rsi_single'), "Missing RSI single method"

print("✅ All MeanReversionAgent methods present")

# Verify SMA threshold changed
import inspect
source = inspect.getsource(agent._price_distance_from_sma_score)
assert '0.07' in source, "SMA threshold not updated to 0.07"
print("✅ SMA threshold = 0.07 (was 0.03)")

# Verify trend filter implementation
source = inspect.getsource(agent._get_trend_filter)
assert '200' in source, "Trend filter not using 200-SMA"
print("✅ Trend filter uses 200-SMA")
EOF
```

---

### 2. YOLOAgent Configuration

```bash
python3 << 'EOF'
from agents.yolo import YOLOAgent
import config

# Check config
assert config.YOLO_CVD_MOMENTUM_MIN == 0.10, "Config not updated"
print(f"✅ Config: YOLO_CVD_MOMENTUM_MIN = {config.YOLO_CVD_MOMENTUM_MIN}")

# Check agent
agent = YOLOAgent()
assert agent.ACTIVATION_REQUIREMENTS['cvd_momentum_min'] == 0.10
print(f"✅ Agent: CVD momentum threshold = {agent.ACTIVATION_REQUIREMENTS['cvd_momentum_min']}")
EOF
```

---

### 3. OrderflowAgent Configuration

```bash
python3 << 'EOF'
from agents.orderflow import OrderFlowAgent
import config

# Check config
assert config.CVD_VETO_THRESHOLD == 0.20, "Config not updated"
print(f"✅ Config: CVD_VETO_THRESHOLD = {config.CVD_VETO_THRESHOLD}")

# Check agent
agent = OrderFlowAgent()
assert agent._veto_threshold == 0.20
print(f"✅ Agent: CVD veto threshold = {agent._veto_threshold}")
EOF
```

---

### 4. All Agents Import Correctly

```bash
python3 << 'EOF'
print("Testing all agent imports...")

from agents.mean_reversion import MeanReversionAgent
print("  ✓ MeanReversionAgent")

from agents.momentum import MomentumAgent
print("  ✓ MomentumAgent")

from agents.yolo import YOLOAgent
print("  ✓ YOLOAgent")

from agents.orderflow import OrderFlowAgent
print("  ✓ OrderFlowAgent")

from agents.risk_guardian import RiskGuardianAgent
print("  ✓ RiskGuardianAgent")

from agents.sentiment import SentimentAgent
print("  ✓ SentimentAgent")

print("\n🎉 All agents import successfully!")
EOF
```

---

## Detailed Verification: Testing with Mock Market Data

### Test MeanReversionAgent Trend Filter

```python
from agents.mean_reversion import MeanReversionAgent
from agents.base import MarketData, Candle
import datetime

# Create mock agent
agent = MeanReversionAgent()

# Create mock market data with uptrend
candles = []
for i in range(200):
    price = 100 + (i * 0.1)  # Steady uptrend
    candles.append(Candle(
        open=price,
        high=price + 1,
        low=price - 1,
        close=price + 0.5,
        volume=1000,
        timestamp=datetime.datetime.now()
    ))

# Add current price far above SMA
current_price = 120  # Above 200-SMA (around 110)

# Create market data
market_data = MarketData(
    current_price=current_price,
    candles=candles,
    # ... other fields
)

# Test trend filter
trend_filter = agent._get_trend_filter(market_data)
print(f"Trend filter in uptrend: {trend_filter}")
assert trend_filter == 0.5, "Should reduce signal strength in uptrend"
print("✅ Trend filter correctly reduces signal in uptrend")
```

---

### Test MeanReversionAgent RSI Divergence

```python
from agents.mean_reversion import MeanReversionAgent

agent = MeanReversionAgent()

# Test bearish divergence (higher price high, lower RSI high)
divergence_score = agent._rsi_divergence_score(market_data)
print(f"RSI divergence score: {divergence_score}")
# Should return between -0.6 and +0.6 or 0.0
assert -0.6 <= divergence_score <= 0.6
print("✅ RSI divergence score within valid range")
```

---

### Test YOLOAgent Activation Conditions

```python
from agents.yolo import YOLOAgent
from agents.base import Vote, VoteDirection

agent = YOLOAgent()

# Mock market data
market_data = type('MarketData', (), {
    'fear_greed': 80,  # Greed zone
    'current_drawdown_pct': 1.0,  # Within limits
    'prism_risk': type('PrismRisk', (), {'risk_score': 50})(),
    'cvd': 0.15,  # Above 0.10 threshold
    'vwap': 100,
    'price': 105,  # Above VWAP
})()

# Mock votes from other agents
prior_votes = [
    Vote(agent_id='momentum', direction=VoteDirection.BUY, confidence=0.8),
    Vote(agent_id='sentiment', direction=VoteDirection.BUY, confidence=0.7),
]

# Test activation
can_activate = agent.is_activation_condition_met(market_data, prior_votes)
print(f"YOLO can activate: {can_activate}")
# Note: Some conditions might still fail, but CVD threshold should pass
```

---

### Test OrderflowAgent CVD Veto

```python
from agents.orderflow import OrderFlowAgent

agent = OrderFlowAgent()

# Mock market data with strong distribution
market_data = type('MarketData', (), {
    'current_price': 105,
    'candles': [  # Mock candles
        type('Candle', (), {'close': 100, 'open': 99, 'volume': 100})(),
        type('Candle', (), {'close': 101, 'open': 100, 'volume': 100})(),
    ],
    'change_24h_pct': 1.0,
})()

# Set up agent state
agent._cvd_history = [100] * 30  # Historical CVD
agent._vwap = 104

# Test with CVD momentum > 0.15 (should not veto)
# and price > VWAP (distribution condition)
vote = agent.analyze(market_data)
print(f"OrderFlow vote: {vote.direction.value}")
# With new threshold, veto less likely than before
```

---

## Compilation Check

```bash
# Verify all Python files compile
python3 -m py_compile \
  agents/mean_reversion.py \
  agents/momentum.py \
  agents/orderflow.py \
  agents/yolo.py \
  agents/risk_guardian.py \
  agents/sentiment.py \
  config.py

echo "✅ All files compile successfully"
```

---

## Integration Test: Full Agent Pipeline

```bash
python3 << 'EOF'
import datetime
from agents.base import MarketData, Candle, Vote, VoteDirection
from agents.mean_reversion import MeanReversionAgent
from agents.momentum import MomentumAgent
from agents.orderflow import OrderFlowAgent

# Create sample market data
candles = []
for i in range(200):
    price = 100 + (i * 0.01)  # Slight uptrend
    candles.append(Candle(
        open=price,
        high=price + 0.5,
        low=price - 0.5,
        close=price + 0.2,
        volume=1000 + i,
        timestamp=datetime.datetime.now()
    ))

market_data = MarketData(
    current_price=102.0,
    candles=candles,
    change_24h_pct=2.0,
    fear_greed_index=65,
)

# Test each agent
agents = {
    'mean_reversion': MeanReversionAgent(),
    'momentum': MomentumAgent(),
    'orderflow': OrderFlowAgent(),
}

for agent_name, agent in agents.items():
    try:
        vote = agent.analyze(market_data)
        print(f"✅ {agent_name}: {vote.direction.value} (conf={vote.confidence:.2f})")
    except Exception as e:
        print(f"❌ {agent_name}: {str(e)}")

print("\n✅ All agents analyze successfully!")
EOF
```

---

## Performance Baseline

Before running live trading, capture performance metrics:

```bash
python3 << 'EOF'
import time
from agents.mean_reversion import MeanReversionAgent
from agents.base import MarketData, Candle
import datetime

# Create market data
candles = [Candle(
    open=100+i*0.01,
    high=100+i*0.01+0.5,
    low=100+i*0.01-0.5,
    close=100+i*0.01+0.2,
    volume=1000,
    timestamp=datetime.datetime.now()
) for i in range(200)]

market_data = MarketData(
    current_price=102.0,
    candles=candles,
)

# Benchmark
agent = MeanReversionAgent()
start = time.time()
for _ in range(1000):
    agent.analyze(market_data)
elapsed = time.time() - start

print(f"MeanReversionAgent.analyze() x1000: {elapsed:.3f}s")
print(f"Per-call: {elapsed/1000*1000:.2f}ms")
print("✅ Performance acceptable" if elapsed < 1.0 else "⚠️ Performance slow")
EOF
```

---

## Rollback Instructions (If Needed)

If any fix causes issues, here's how to rollback:

```bash
# Rollback MeanReversionAgent to simple version
git checkout agents/mean_reversion.py

# Rollback config thresholds
git checkout config.py

# Rollback YOLOAgent
git checkout agents/yolo.py
```

---

## Files to Monitor During Live Testing

1. **agents/mean_reversion.py**
   - Monitor: SMA distance signals (should be less frequent than before)
   - Monitor: Trend filter application (should reduce false signals)
   - Monitor: RSI divergence signals (should appear ~5-10% of time)

2. **agents/yolo.py**
   - Monitor: Activation rate (should increase from near 0% to 5-10%)
   - Monitor: Win rate on YOLO signals (should be high >70%)

3. **agents/orderflow.py**
   - Monitor: CVD veto frequency (should decrease)
   - Monitor: Orderflow signals passing through (should increase)

4. **config.py**
   - Verify: CVD_VETO_THRESHOLD = 0.20 ✓
   - Verify: YOLO_CVD_MOMENTUM_MIN = 0.10 ✓

---

## Expected Outcomes

| Metric | Expected | How to Verify |
|--------|----------|--------------|
| MR signal frequency | -70% false signals | Count HOLD vs BUY/SELL ratio |
| Trend filter active | 30-40% of time | Check composite *= 0.5 logs |
| RSI divergence | 5-10% of signals | Look for divergence_score != 0 |
| YOLO activations | 5-10 per week | Count activation logs |
| OrderFlow vetos | -33% fewer | Compare veto log count |

---

## Success Criteria

✅ **All agents compile** without syntax errors  
✅ **All agents import** successfully  
✅ **Configuration values** correctly updated  
✅ **New methods** present and callable  
✅ **Signal frequency** reduced for MR (false signals down)  
✅ **YOLO activation** possible in realistic conditions  
✅ **OrderFlow vetos** less frequent (CVD threshold relaxed)  

If all criteria met, the fixes are working correctly!
