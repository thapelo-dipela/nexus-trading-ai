# ERC-8004 Compliance Audit Report

**Date:** April 12, 2026  
**Project:** NEXUS Trading AI  
**Status:** ⛔ **CRITICAL NON-COMPLIANCE**

---

## Executive Summary

Your project **violates multiple core ERC-8004 requirements**. Trades are being submitted directly to Kraken CLI instead of through the RiskRouter contract. On-chain integration is stubbed but not functional. This means:

- ❌ **Leaderboard scoring:** Invalid (trades not verified on-chain)
- ❌ **Reputation system:** Not working (no checkpoints posted)
- ❌ **Sandbox capital:** Not claimed (0.05 ETH allocation unused)
- ❌ **Risk controls:** Not enforced (bypassing RiskRouter limits)
- ❌ **Compliance validation:** Disabled (not going through ValidationRegistry)

**Severity:** CRITICAL — Project as-is will not qualify for competition judging.

---

## Audit Findings

### 1. ❌ CRITICAL: Network Configuration Wrong

**Issue:** RPC URL points to Base Sepolia instead of Ethereum Sepolia

```python
# config.py line 47
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")  # ← WRONG
```

**Required:** Ethereum Sepolia (Chain ID: 11155111)

```python
RPC_URL = "https://sepolia.infura.io/v3/YOUR_KEY"
# OR
RPC_URL = "https://rpc.sepolia.org"
```

**Impact:** All contract calls to wrong network. Reputation, validation, vault claims all fail.

---

### 2. ❌ CRITICAL: Trades Bypass RiskRouter

**Current Implementation:**
```python
# main.py line 339
kraken_client.market_buy(volume)  # Direct Kraken CLI call

# execution/kraken.py line 24
def market_buy(self, volume: float) -> Dict[str, Any]:
    """Execute market buy order directly via Kraken CLI"""
    # Bypasses ALL contract validation
```

**Required:** All trades through RiskRouter contract

```typescript
// CORRECT: Submit through RiskRouter
const tradeIntent = {
  agentId: agentId,
  agentWallet: agentWalletAddress,
  pair: "XBTUSD",
  action: "BUY",
  amountUsdScaled: 50000,  // $500 * 100
  maxSlippageBps: 100,
  nonce: currentNonce,
  deadline: Math.floor(Date.now() / 1000) + 300
};

const signature = await agentWallet.signTypedData(domain, types, tradeIntent);
await router.submitTradeIntent(tradeIntent, signature);
```

**Impact:** 
- ❌ Risk limits not enforced (can trade $1000+, violates $500 max)
- ❌ Rate limiting not enforced (can trade >10x/hour)
- ❌ Trades invisible to leaderboard
- ❌ No on-chain audit trail

---

### 3. ❌ CRITICAL: Contract Addresses Not Configured

**Issue:** All contract addresses missing or empty

```python
# config.py lines 60-62
REPUTATION_REGISTRY_ADDRESS = os.getenv("REPUTATION_REGISTRY_ADDRESS", "")  # Empty
VALIDATION_REGISTRY_ADDRESS = os.getenv("VALIDATION_REGISTRY_ADDRESS", "")  # Empty
```

**Required Addresses (DO NOT CHANGE):**
```python
AGENT_REGISTRY_ADDRESS = "0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3"
HACKATHON_VAULT_ADDRESS = "0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90"
RISK_ROUTER_ADDRESS = "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC"
REPUTATION_REGISTRY_ADDRESS = "0x423a9904e39537a9997fbaF0f220d79D7d545763"
VALIDATION_REGISTRY_ADDRESS = "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1"
```

**Impact:** No agent registration, no vault claims, no on-chain reputation.

---

### 4. ❌ CRITICAL: Agent Registration Missing

**Current:** Agent ID generation is manual/local JSON only

```python
# Agents created but NOT registered on-chain
agents = create_default_agents()  # Local objects only
```

**Required:** Register on AgentRegistry to get valid agentId

```typescript
npm run register  # Calls AgentRegistry.register()
```

**Impact:** Agent has no on-chain identity, cannot claim sandbox capital.

---

### 5. ❌ CRITICAL: Sandbox Capital Not Claimed

**Current:** No vault interaction

```python
# No call to HackathonVault.claimAllocation()
# Missing: 0.05 ETH sandbox capital
```

**Required:** Claim after registration

```typescript
const vault = new ethers.Contract(
  HACKATHON_VAULT_ADDRESS,
  ["function claimAllocation(uint256 agentId) external"],
  signer
);
await vault.claimAllocation(agentId);
```

**Impact:** No budget for trades. Transactions would fail if we tried to use it.

---

### 6. ❌ CRITICAL: Checkpoints Not Posted to ValidationRegistry

**Current:** No ValidationRegistry integration

```python
# onchain/reputation.py - push_outcome() returns mock data
# Real ValidationRegistry.postEIP712Attestation() never called
```

**Required:** Post signed checkpoint after every decision

```typescript
await validationRegistry.postEIP712Attestation(
  agentId,
  checkpointHash,    // EIP-712 digest
  score,              // 0-100
  notes               // JSON string of reasoning
);
```

**Impact:** Validators can't score your agent. Reputation doesn't accumulate.

---

### 7. ⚠️ MAJOR: Agent Voting Power Not Properly Penalized

**Current Implementation:**
```python
# consensus/engine.py - Linear penalties
agent.weight -= 0.05 * confidence  # Linear decay

# No exponential penalty for consecutive losses
# No streak tracking
```

**Requirements:**
- Consecutive wins → exponential weight increase
- Consecutive losses → exponential weight decrease
- Streak tracking: Track win/loss streaks
- Decay formula: `weight = initial * (0.9 ^ consecutive_losses)`

**Impact:** Poor agents stay in voting power longer than allowed.

---

### 8. ⚠️ MAJOR: Rate Limiting Not Enforced

**Current:** Config constants exist but no runtime enforcement

```python
# config.py
MAX_TRADE_SIZE_USD = 500.0          # Config exists
LOOP_INTERVAL_SECONDS = 300         # But no actual checking

# main.py - No rate limiter checks before executing trades
kraken_client.market_buy(volume)  # Can buy any amount
```

**Required:**
- Max $500 per trade (enforced before each trade)
- Max 10 trades per hour (tracked and rejected if exceeded)
- Max 5% drawdown (checked against portfolio)

**Implementation needed:**
```python
# Create execution/rate_limiter.py
class RateLimiter:
    def __init__(self, max_trades_per_hour=10, max_trade_size_usd=500, max_drawdown_pct=5):
        self.max_trades_per_hour = max_trades_per_hour
        self.max_trade_size_usd = max_trade_size_usd
        self.max_drawdown_pct = max_drawdown_pct
        self.trade_history = []
        self.peak_portfolio_value = None
    
    def check_trade_allowed(self, trade_size_usd, current_portfolio_value):
        # 1. Check size limit
        if trade_size_usd > self.max_trade_size_usd:
            return False, f"Trade size ${trade_size_usd} exceeds max ${self.max_trade_size_usd}"
        
        # 2. Check hourly rate limit
        recent_trades = [t for t in self.trade_history if t > time.time() - 3600]
        if len(recent_trades) >= self.max_trades_per_hour:
            return False, f"Hit hourly limit: {len(recent_trades)} trades in last hour"
        
        # 3. Check drawdown limit
        if self.peak_portfolio_value is None:
            self.peak_portfolio_value = current_portfolio_value
        
        drawdown = (self.peak_portfolio_value - current_portfolio_value) / self.peak_portfolio_value
        if drawdown > self.max_drawdown_pct / 100:
            return False, f"Drawdown {drawdown*100:.1f}% exceeds max {self.max_drawdown_pct}%"
        
        self.peak_portfolio_value = max(self.peak_portfolio_value, current_portfolio_value)
        return True, "OK"
    
    def record_trade(self):
        self.trade_history.append(time.time())
```

**Impact:** Risk controls not enforced. Could violate competition limits.

---

### 9. ⚠️ MAJOR: Dashboard Not Showing Live Contract Events

**Current:** Dashboard shows local JSON files (static data)

```typescript
// No event listeners for contract events
// No real-time reputation updates
// No position tracking from on-chain
```

**Required:** Listen to contract events and display in real-time

```typescript
router.on("TradeApproved", (agentId, tradeHash, executedPrice) => {
  // Update dashboard with trade
});

router.on("TradeRejected", (agentId, reason) => {
  // Show rejection reason
});

repRegistry.on("ScoreUpdated", (agentId, newScore) => {
  // Update agent reputation in real-time
});
```

**Impact:** Dashboard shows stale data. Real-time monitoring not working.

---

### 10. ⚠️ MEDIUM: Agent Learning Penalties Sub-Optimal

**Current:** Only basic learning implemented

```python
# Linear adjustment when trade closes
agent.weight -= 0.05 * confidence  # Fixed penalty

# No streak bonus/penalty
# No exponential backoff
```

**Better Approach:**
```python
# Track consecutive outcomes
agent.consecutive_wins = 0
agent.consecutive_losses = 0

# Apply exponential penalties for streaks
if trade_won:
    agent.consecutive_wins += 1
    agent.consecutive_losses = 0
    multiplier = 1.1 ** agent.consecutive_wins  # Exponential bonus
    agent.weight *= multiplier
else:
    agent.consecutive_losses += 1
    agent.consecutive_wins = 0
    multiplier = 0.9 ** agent.consecutive_losses  # Exponential penalty
    agent.weight *= multiplier
```

**Impact:** Suboptimal agent selection, but not competition-breaking.

---

## Compliance Checklist

| Requirement | Status | Evidence |
|---|---|---|
| Use Sepolia testnet (11155111) | ❌ FAIL | RPC points to Base Sepolia |
| Use shared contract addresses | ❌ FAIL | Addresses empty in config |
| Register agent on AgentRegistry | ❌ FAIL | No on-chain registration |
| Claim sandbox capital (0.05 ETH) | ❌ FAIL | HackathonVault never called |
| Submit trades through RiskRouter | ❌ FAIL | Trades go direct to Kraken |
| Enforce $500 max trade size | ❌ FAIL | No runtime enforcement |
| Enforce 10 trades/hour limit | ❌ FAIL | No runtime enforcement |
| Enforce 5% max drawdown | ❌ FAIL | No runtime enforcement |
| Post checkpoints to ValidationRegistry | ❌ FAIL | No checkpoint posting |
| Accumulate reputation | ❌ FAIL | Reputation registry not called |
| Use exponential agent penalties | ⚠️ PARTIAL | Linear only, no streaks |
| Dashboard shows live contract events | ❌ FAIL | Shows static JSON |

**Overall Score: 0/12 CRITICAL REQUIREMENTS MET**

---

## Fixed vs. Non-Compliant

### ✅ What's Already Working (Non-Critical)
- Position tracking with stop-loss/take-profit
- Agent consensus voting (local)
- Market regime detection
- Compliance engine (local rules)
- Kraken CLI integration
- Equity curve recording

### ❌ What's Broken (ERC-8004 Critical)
- Network configuration
- Contract integration
- Agent registration
- Trade intent submission
- Sandbox capital claiming
- Checkpoint posting
- Rate limiting enforcement

---

## Path Forward

### IMMEDIATE (Today - 2 hours)
1. Fix RPC URL to Sepolia
2. Add all 5 contract addresses to config.py
3. Create `.env` with all contract addresses and private key
4. Register agent on AgentRegistry
5. Claim sandbox capital from HackathonVault

### HIGH PRIORITY (This week - 8 hours)
1. Refactor trade execution to go through RiskRouter instead of direct Kraken
2. Implement rate limiter and enforce at trade time
3. Add checkpoint posting to ValidationRegistry after each decision
4. Update dashboard to listen to contract events

### MEDIUM PRIORITY (Before submission - 4 hours)
1. Add exponential penalties for consecutive agent losses
2. Add reputation score display from ReputationRegistry
3. Create audit trail in checkpoints.jsonl
4. Test full flow on Sepolia testnet

---

## Code Changes Required

See accompanying file: **ERC8004_IMPLEMENTATION_REQUIRED.md**

---

## Testing & Verification

Once compliant, verify with:

```bash
# 1. Check network
python3 -c "from web3 import Web3; w3=Web3(Web3.HTTPProvider('https://sepolia.infura.io/v3/YOUR_KEY')); print('Chain ID:', w3.eth.chain_id)"

# 2. Read agent ID
cat agent-id.json

# 3. Check vault balance
npx ethers call 0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90 "getBalance(uint256)" 123 --rpc-url https://sepolia.infura.io/v3/YOUR_KEY

# 4. Monitor trade events
npx ethers listen-event 0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC "TradeApproved" --rpc-url https://sepolia.infura.io/v3/YOUR_KEY

# 5. Check reputation
npx ethers call 0x423a9904e39537a9997fbaF0f220d79D7d545763 "getAverageScore(uint256)" 123 --rpc-url https://sepolia.infura.io/v3/YOUR_KEY
```

---

## Summary

Your project is **not ready for competition submission**. It has zero on-chain integration despite being for an on-chain hackathon. All 7 critical audit issues must be resolved before judging.

**Estimated fix time:** 12-16 hours of focused development.

**Next step:** Follow implementation plan in **ERC8004_IMPLEMENTATION_REQUIRED.md**

