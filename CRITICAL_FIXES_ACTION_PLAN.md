# NEXUS Critical Fixes - Action Plan

## Overview
Based on your audit, 7 critical issues were found. **3 are fixed**, **4 need attention**. This document provides step-by-step fixes for the remaining issues.

---

## Priority 1: Fix RPC Network Configuration

### Issue
`config.py` points to Base Sepolia (wrong chain) instead of Ethereum Sepolia testnet.

### Current Code (WRONG)
```python
# config.py line 47
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")  # ❌ Base Sepolia (chain 84532)
```

### Fix Required
```python
# Replace with Ethereum Sepolia testnet:
RPC_URL = os.getenv("RPC_URL", "https://sepolia.infura.io/v3/YOUR_INFURA_KEY")  # ✅ Correct
```

### Alternative URLs (pick one):
```python
# Option 1: Infura (most reliable)
RPC_URL = "https://sepolia.infura.io/v3/YOUR_INFURA_KEY"

# Option 2: Alchemy
RPC_URL = "https://eth-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY"

# Option 3: Quicknode
RPC_URL = "https://eth-sepolia-rpc.quicknode.pro/YOUR_KEY"

# Option 4: Public (slower but free)
RPC_URL = "https://rpc.sepolia.org"
```

### Verification
```bash
# After fix, verify:
python3 -c "
from web3 import Web3
rpc = 'https://sepolia.infura.io/v3/YOUR_KEY'
w3 = Web3(Web3.HTTPProvider(rpc))
print(f'Connected: {w3.is_connected()}')
print(f'Chain ID: {w3.eth.chain_id}')  # Should be 11155111
"
```

---

## Priority 2: Implement Contract Integration

### Issue
5 hackathon contracts exist but are never called. Currently only returning mock data.

### Current Code (STUB ONLY)
```python
# onchain/reputation.py
def push_outcome(self, signed_outcome, dry_run=False):
    """Push outcome to on-chain reputation registry."""
    if dry_run:
        logger.info(f"[dim]DRY-RUN: Would push outcome on-chain[/dim]")
        return True
    
    # ❌ NO ACTUAL CONTRACT CALL - just returns mock
    return {"status": "success", "transaction": "mock_tx"}
```

### Fix Required: Implement Web3 Integration

Step 1: Install Web3.py
```bash
pip install web3
```

Step 2: Create Web3 client in `onchain/reputation.py`
```python
from web3 import Web3
from web3.contract import Contract
import json

class ReputationClient:
    def __init__(self, rpc_url=None, contract_address=None, private_key=None):
        self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://sepolia.infura.io/v3/YOUR_KEY")
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        
        self.contract_address = contract_address or os.getenv("REPUTATION_REGISTRY_ADDRESS")
        self.private_key = private_key or os.getenv("AGENT_WALLET_KEY")
        
        # Load ABI from contract file
        with open("ai-trading-agent-template/contracts/ReputationRegistry.sol", "r") as f:
            # Parse or load ABI here
            pass
        
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=abi)
    
    def push_outcome(self, signed_outcome, dry_run=False):
        """Actually call ReputationRegistry.recordOutcome()"""
        if dry_run:
            logger.info("[dim]DRY-RUN: Would push outcome on-chain[/dim]")
            return True
        
        try:
            # Build transaction
            tx = self.contract.functions.recordOutcome(
                signed_outcome["trade_id"],
                signed_outcome["direction"],
                signed_outcome["pnl_usd"],
                signed_outcome["agent_votes"]
            ).build_transaction({
                'from': self.account.address,
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
            })
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            logger.info(f"[green]✓ Outcome pushed on-chain: {tx_hash.hex()}[/green]")
            return {"status": "success", "transaction": tx_hash.hex()}
            
        except Exception as e:
            logger.error(f"[red]Failed to push outcome: {e}[/red]")
            return False
```

### Contracts to Integrate
1. **ReputationRegistry.sol** - Record trade outcomes
   - Function: `recordOutcome(tradeId, direction, pnlUsd, agentVotes)`

2. **ValidationRegistry.sol** - Validate trades
   - Function: `validateTrade(tradeId, riskScore, assets)`

3. **HackathonVault.sol** - Manage capital
   - Function: `claimCapital(agentId, amount)`

4. **RiskRouter.sol** - Route based on risk
   - Function: `assessRisk(tradeId, volatility)`

5. **AgentRegistry.sol** - Register agents
   - Function: `registerAgent(agentId, strategyType)`

### Verification
```bash
# Check contract addresses are set
grep -E "REPUTATION_REGISTRY_ADDRESS|VALIDATION_REGISTRY_ADDRESS" config.py

# After implementation, check logs for actual transaction hashes
tail -50 nexus_debug.log | grep "Outcome pushed on-chain"
```

---

## Priority 3: Add Rate Limit Enforcement

### Issue
Max 10 trades/hour and $500/trade limits exist in config but aren't enforced at runtime.

### Current Code (NO ENFORCEMENT)
```python
# config.py
MAX_TRADE_SIZE_USD = 500.0              # ❌ Just a constant, not enforced
MIN_TRADE_SIZE_USD = 10.0
MAX_LEVERAGE = 3.0
MAX_DRAWDOWN_PCT = 5.0
```

### Fix Required: Add Runtime Guards

Create `execution/rate_limiter.py`:
```python
import time
import logging
from typing import Dict, List
from datetime import datetime, timedelta
import config

logger = logging.getLogger(__name__)

class RateLimiter:
    """Enforce trading rate limits."""
    
    def __init__(self):
        self.trades_last_hour: List[int] = []  # Timestamps
        self.total_traded_today_usd: float = 0.0
        self.last_reset_hour = datetime.now()
        self.last_reset_day = datetime.now()
    
    def _cleanup_stale_trades(self):
        """Remove trades older than 1 hour."""
        cutoff = time.time() - 3600  # 1 hour ago
        self.trades_last_hour = [t for t in self.trades_last_hour if t > cutoff]
    
    def can_execute_trade(self, trade_size_usd: float) -> tuple[bool, str]:
        """
        Check if trade can execute.
        Returns: (can_execute, reason)
        """
        self._cleanup_stale_trades()
        
        # Check 1: Individual trade size
        if trade_size_usd > config.MAX_TRADE_SIZE_USD:
            return False, f"Trade ${trade_size_usd:.2f} exceeds max ${config.MAX_TRADE_SIZE_USD:.2f}"
        
        if trade_size_usd < config.MIN_TRADE_SIZE_USD:
            return False, f"Trade ${trade_size_usd:.2f} below min ${config.MIN_TRADE_SIZE_USD:.2f}"
        
        # Check 2: Trades per hour (max 10)
        if len(self.trades_last_hour) >= 10:
            return False, f"Reached max 10 trades/hour ({len(self.trades_last_hour)} already executed)"
        
        # Check 3: Daily capital limit (example: $5000/day)
        daily_limit = config.MAX_TRADE_SIZE_USD * 10  # 10 trades max
        if self.total_traded_today_usd + trade_size_usd > daily_limit:
            return False, f"Daily limit ${daily_limit:.2f} would be exceeded"
        
        return True, "OK"
    
    def record_trade(self, trade_size_usd: float):
        """Record executed trade for rate limiting."""
        self.trades_last_hour.append(time.time())
        self.total_traded_today_usd += trade_size_usd
        logger.info(f"[cyan]Trade recorded: ${trade_size_usd:.2f} | Hour: {len(self.trades_last_hour)}/10[/cyan]")
```

### Integrate into `main.py`

Add to imports:
```python
from execution.rate_limiter import RateLimiter
```

Create limiter:
```python
def live_trading_loop(dry_run: bool = False):
    rate_limiter = RateLimiter()
    # ... rest of initialization ...
```

Check before execution:
```python
# In trade_cycle(), before executing trade:
can_trade, reason = rate_limiter.can_execute_trade(position_size_usd)
if not can_trade:
    logger.warning(f"[yellow]Trade blocked by rate limiter: {reason}[/yellow]")
    return True

# After successful execution:
if not dry_run:
    rate_limiter.record_trade(position_size_usd)
```

### Verification
```bash
# After 10 trades in 1 hour, system should reject 11th:
grep "Trade blocked by rate limiter" nexus_debug.log

# Should see exactly 10 trades/hour:
grep "Trade recorded:" nexus_debug.log | wc -l  # Should be <= 10 per hour
```

---

## Priority 4: Add Exponential Agent Penalties

### Issue
Consecutive losses don't apply escalating penalties. Linear penalties don't properly punish bad agents.

### Current Code (LINEAR ONLY)
```python
# consensus/engine.py
if pnl_usd > 0:
    adjustment = 0.05 * confidence
    agent.weight = min(agent.weight + adjustment, 2.0)
else:
    adjustment = 0.05 * confidence  # ❌ Same adjustment regardless of streak
    agent.weight = max(agent.weight - adjustment, 0.1)
```

### Fix Required: Track Streaks and Exponential Decay

Update `agents/base.py`:
```python
@dataclass
class Agent:
    """Base agent with streak tracking."""
    agent_id: str
    weight: float = 1.0
    consecutive_losses: int = 0  # NEW
    consecutive_wins: int = 0    # NEW
    pnl_total: float = 0.0
    trades_closed: int = 0
    wins: int = 0
    losses: int = 0
```

Update `consensus/engine.py`:
```python
def record_outcome(self, direction_str, confidence, votes, pnl_usd, current_price):
    """Update agent weights with exponential penalties."""
    
    for vote in votes:
        agent_id = vote.agent_id
        agent = self.agents.get(agent_id)
        if not agent:
            continue
        
        is_correct = (vote.direction.value == direction_str and pnl_usd > 0) or \
                     (vote.direction.value != direction_str and pnl_usd < 0)
        
        if is_correct:
            # Winning trade
            agent.consecutive_wins += 1
            agent.consecutive_losses = 0  # Reset streak
            
            # Reward proportional to streak
            bonus = 0.05 * (1 + agent.consecutive_wins * 0.1)
            adjustment = bonus * confidence
            agent.weight = min(agent.weight + adjustment, 2.0)
            
            logger.debug(f"✓ {agent_id}: +{adjustment:.4f} (streak: {agent.consecutive_wins})")
        
        else:
            # Losing trade
            agent.consecutive_losses += 1
            agent.consecutive_wins = 0  # Reset streak
            
            # Exponential penalty: 1x, 2x, 4x, 8x, ...
            penalty_multiplier = 2 ** (agent.consecutive_losses - 1)
            base_penalty = 0.05 * confidence
            adjustment = base_penalty * penalty_multiplier
            
            agent.weight = max(agent.weight - adjustment, 0.1)
            
            logger.debug(f"✗ {agent_id}: -{adjustment:.4f} (streak: {agent.consecutive_losses}, multiplier: {penalty_multiplier}x)")
        
        # Save updated agent
        self.save_weights()
```

### Verification
```bash
# After several losing trades, weight should drop exponentially:
cat nexus_weights.json | jq '.[] | {agent_id, weight, losses, consecutive_losses}'

# Example: After 3 consecutive losses:
# Loss 1: -0.05 weight
# Loss 2: -0.10 weight (2x)
# Loss 3: -0.20 weight (4x)
# Total: -0.35 weight for 3 consecutive losses
```

---

## Implementation Order (Recommended)

### Week 1 (Critical):
1. **Fix RPC Config** (15 minutes) - Enable contract calls to work
2. **Add Rate Limiter** (1 hour) - Prevent runaway capital usage
3. **Test both fixes** (30 minutes) - Verify working

### Week 2 (Important):
1. **Contract Integration** (2-3 hours) - Connect to on-chain reputation
2. **Exponential Penalties** (1 hour) - Better agent learning
3. **Full integration test** (1 hour) - End-to-end flow

### Result:
All 7 audit findings addressed ✅

---

## Testing Checklist

After each fix:

```bash
# Test 1: System still runs
./run_live.sh --dry-run --verbose

# Test 2: No new errors
grep -i "error\|exception" nexus_debug.log | wc -l  # Should be 0 or very low

# Test 3: Feature working
# (Check specific test for each feature above)

# Test 4: Performance okay
ps aux | grep python3 | grep main.py  # Check CPU/memory
```

---

## Document References
- Original audit findings: Your initial message
- Current implementation: `IMPLEMENTATION_SUMMARY.md`
- Trading guide: `LIVE_SETUP_COMPLETE.md`

