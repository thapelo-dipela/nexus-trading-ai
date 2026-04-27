# Trade Block Mechanism — Loss Prevention

**Date**: April 13, 2026  
**Status**: ✅ IMPLEMENTED  
**Feature**: Automatic trading halts when repeated losses detected  

---

## Overview

The **Trade Block Mechanism** prevents the system from continuing to lose money by automatically blocking a trade direction (BUY or SELL) after 3 consecutive losing trades in that direction.

**Key Metrics:**
- **Trigger**: 3+ consecutive losses in same direction
- **Action**: Block that direction for 6 trading cycles
- **Effect**: Force opposite direction (BUY-only or SELL-only mode)
- **Reset**: Win resets loss streak to 0

---

## How It Works

### Trade Flow

```
Trade closes with loss
    ↓
Check if BUY or SELL
    ↓
Increment loss streak for that direction
    ↓
If loss_streak >= 3:
  • Block that direction for 6 cycles
  • Log WARNING
  • Reset streak
    ↓
Next trade is proposed
    ↓
Check if direction is blocked
    ↓
If blocked:
  • Reject trade with reason "TRADE BLOCKED"
  • Force HOLD
  • Continue for 6 cycles
    ↓
If not blocked:
  • Execute trade normally
```

### Loss Streak & Block Duration

| Event | BUY Streak | BUY Blocked? | SELL Streak | SELL Blocked? |
|-------|-----------|------------|-----------|--------------|
| Start | 0 | ❌ | 0 | ❌ |
| BUY Loss | 1 | ❌ | 0 | ❌ |
| BUY Loss | 2 | ❌ | 0 | ❌ |
| BUY Loss | 3 | ✅ (6 cycles) | 0 | ❌ |
| Cycle passes | 3 | ✅ (5 cycles) | 0 | ❌ |
| BUY Win | **0** ⬇️ | ❌ (reset) | 0 | ❌ |

---

## Implementation Details

### Files Modified

#### 1. `execution/positions.py` — Core Logic

**Added to `PositionManager.__init__`**:
```python
# Trade block mechanism
self.buy_loss_streak = 0        # Consecutive BUY losses
self.sell_loss_streak = 0       # Consecutive SELL losses
self.buy_blocked_cycles = 0     # Cycles remaining for BUY block
self.sell_blocked_cycles = 0    # Cycles remaining for SELL block
self.block_threshold = 3        # Block after 3 consecutive losses
self.block_duration = 6         # Block for 6 cycles
```

**Added to `PositionManager.close_position`**:
- Detects if trade closed at loss
- Increments loss streak for that direction
- Triggers block if streak >= 3
- Resets streak on win

**New methods**:
- `_decrement_trade_blocks()` — Counts down block timers each cycle
- `is_direction_blocked(direction)` — Returns True if blocked
- `get_block_status()` — Returns full block status for dashboard

#### 2. `main.py` — Trade Rejection

**Added after confidence threshold check** (line ~444):
```python
# Check Trade Block
if position_manager.is_direction_blocked(consensus_direction.value):
    # Log warning and force HOLD
    # Continue without executing
```

---

## Example Scenarios

### Scenario 1: Three Consecutive BUY Losses

```
Cycle 1: BUY trade opens and closes with -$50 loss
         → buy_loss_streak = 1
         → buy_blocked_cycles = 0 (not yet triggered)

Cycle 2: BUY trade opens and closes with -$75 loss
         → buy_loss_streak = 2
         → buy_blocked_cycles = 0 (not yet triggered)

Cycle 3: BUY trade opens and closes with -$25 loss
         → buy_loss_streak = 3
         → BLOCK TRIGGERED!
         → buy_blocked_cycles = 6
         → buy_loss_streak = 0 (reset)

Cycle 4: Consensus says BUY
         → CHECK: is_direction_blocked("BUY")?
         → YES! buy_blocked_cycles = 6
         → REJECT: "TRADE BLOCKED: BUY blocked for 6 more cycle(s)"
         → HOLD instead of BUY
         → buy_blocked_cycles = 5 (decremented)

Cycles 5-9: Same rejection, buy_blocked_cycles counts down
           5 → 4 → 3 → 2 → 1

Cycle 10: buy_blocked_cycles = 0
          → BUY block lifted ✓
          → Next BUY consensus will execute normally
```

### Scenario 2: Win Resets Streak (No Block)

```
Cycle 1: BUY trade loses -$50
         → buy_loss_streak = 1

Cycle 2: BUY trade loses -$75
         → buy_loss_streak = 2

Cycle 3: BUY trade WINS +$100
         → buy_loss_streak = 0 (RESET!)
         → buy_blocked_cycles = 0
         → No block triggered

Cycle 4: BUY trade loses -$30
         → buy_loss_streak = 1 (fresh start)
```

### Scenario 3: Opposite Direction During Block

```
Scenario: BUY is blocked for 6 cycles

Cycle 4: Consensus says BUY
         → BLOCKED for 6 cycles
         → HOLD (no trade)
         → buy_blocked_cycles = 5

Cycle 5: Consensus says SELL
         → CHECK: is_direction_blocked("SELL")?
         → NO! sell_blocked_cycles = 0
         → EXECUTE SELL normally ✓
         → If it loses: sell_loss_streak += 1
```

---

## Dashboard Integration

The block status is available in the dashboard via `get_block_status()`:

```json
{
  "buy_blocked": true,
  "buy_cycles_remaining": 4,
  "buy_loss_streak": 0,
  "sell_blocked": false,
  "sell_cycles_remaining": 0,
  "sell_loss_streak": 1
}
```

**Display suggests:**
- 🔴 BUY blocked for 4 more cycles
- 🟢 SELL active (1 loss in streak)

---

## Configuration

These values are hard-coded in `PositionManager.__init__`:

```python
self.block_threshold = 3      # How many losses to trigger block
self.block_duration = 6       # How many cycles to block for
```

To adjust:
1. Edit `execution/positions.py` lines 74-75
2. Restart the trading system

**Recommendations**:
- `block_threshold = 3` — Prevents immediate blocking on unlucky streak
- `block_duration = 6` — Long enough to cool off, short enough to recover
- `block_duration = 10` — More conservative approach
- `block_threshold = 2` — More aggressive protection

---

## Expected Impact

### Before Trade Block
```
Cycle 1: BUY consensus → loses -$50
Cycle 2: BUY consensus → loses -$75
Cycle 3: BUY consensus → loses -$25 (still trading)
Cycle 4: BUY consensus → loses -$40 (compounding losses!)
Total damage: -$190 in repeated bad trades
```

### After Trade Block
```
Cycle 1: BUY consensus → loses -$50 (buy_loss_streak = 1)
Cycle 2: BUY consensus → loses -$75 (buy_loss_streak = 2)
Cycle 3: BUY consensus → loses -$25 (BLOCK TRIGGERED → buy_loss_streak = 0, blocked for 6 cycles)
Cycle 4: BUY consensus → REJECTED (blocked) → HOLD
Cycle 5: BUY consensus → REJECTED (blocked) → HOLD
Cycle 6: BUY consensus → REJECTED (blocked) → HOLD
Cycles 7-9: BUY consensus → REJECTED (blocked) → HOLD
Cycle 10: BUY block lifted, can trade normally again
Total damage: -$150 (prevented 2-3 more losses)
Savings: $40-80 per blocked direction
```

### Annual Impact
- Assuming 5 trade blocks per year
- Each prevents $40-80 in losses
- **Total annual savings: $200-400**

---

## Logging Output

When loss streak triggers block:
```
[red]TRADE BLOCK ACTIVATED[/red]: BUY blocked for 6 cycles (after 3 consecutive losses)
```

When trade is rejected due to block:
```
[red]TRADE BLOCKED[/red]: BUY blocked for 5 more cycle(s) due to repeated losses
```

When block is lifted:
```
[green]✓ BUY block lifted[/green]
```

---

## Edge Cases

### Edge Case 1: Closed Position During Block
If a position opens during block and closes later:
- Block is NOT lifted automatically
- Block only counts down via cycle iterations
- Position closure just records the loss (or win)

### Edge Case 2: Multiple SELL Blocks
If both BUY and SELL are blocked simultaneously:
- System goes into "HOLD mode" for all cycles
- Consensus ignored until one direction unblocks
- Very rare unless extremely bad performance

### Edge Case 3: Immediate Win After Block Trigger
```
Cycle 3: BUY loses → block triggered
Cycle 4: BUY rejected (blocked) → HOLD
Cycle 4: SELL wins +$100 → sell_loss_streak = 0 (no change)
```
- SELL win does NOT affect BUY block
- Each direction tracked independently

---

## Testing

### Manual Test 1: Verify Loss Tracking
```python
pm = PositionManager()
print(pm.get_block_status())
# {buy_blocked: False, buy_cycles_remaining: 0, buy_loss_streak: 0, ...}
```

### Manual Test 2: Trigger Block (Dry Run)
```python
# Create 3 BUY positions and close each at loss
for i in range(3):
    pos = pm.open_position(f"test_buy_{i}", "BUY", 100, 1.0)
    pm.close_position(pos.trade_id, 95)  # Close at loss

print(pm.get_block_status())
# {buy_blocked: True, buy_cycles_remaining: 6, buy_loss_streak: 0, ...}
```

### Manual Test 3: Block Countdown
```python
# After trigger_block test above:
pm._decrement_trade_blocks()
print(pm.buy_blocked_cycles)  # Should be 5

pm._decrement_trade_blocks()
print(pm.buy_blocked_cycles)  # Should be 4
```

---

## Metrics to Monitor

✅ **Good Signs**:
- `buy_loss_streak` stays at 0-2 (not hitting block threshold)
- Blocks trigger rarely (<1 per month)
- Wins reset streaks quickly

⚠️ **Warning Signs**:
- Blocks trigger frequently (weekly)
- Both BUY and SELL blocks active simultaneously
- Loss streaks hitting 2 regularly (before block)

---

## Future Enhancements

1. **Dynamic Threshold** — Adjust based on market volatility
2. **Graduated Response** — Block at 2 for 3 cycles, at 3 for 6 cycles
3. **Opposite Direction Boost** — Increase opposite direction's weight during block
4. **Learning** — If direction consistently loses, permanently reduce weight
5. **Time-Based Decay** — Decay loss streaks over time (forget old losses)

---

## Summary

✅ **What it does**:
- Tracks consecutive losses per direction
- Blocks direction after 3 consecutive losses
- Prevents trade execution for 6 cycles
- Resets on win

✅ **Expected benefit**:
- Prevents compounding losses: $40-80 per block
- Gives time for market conditions to change
- Forces system to explore opposite direction

✅ **Status**: READY FOR PRODUCTION

