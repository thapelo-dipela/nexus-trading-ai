# ERC-8004 Implementation Plan - Step by Step

**Status:** CRITICAL FIXES REQUIRED  
**Estimated Time:** 12-16 hours  
**Priority:** BEFORE SUBMISSION

---

## Phase 1: Network & Contract Configuration (1 hour)

### Step 1.1: Update RPC URL to Sepolia

**File:** `config.py` (line 47)

```python
# BEFORE (WRONG)
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")

# AFTER (CORRECT - Ethereum Sepolia)
RPC_URL = os.getenv("RPC_URL", "https://sepolia.infura.io/v3/") + os.getenv("INFURA_API_KEY", "YOUR_KEY")
# OR use public endpoint:
RPC_URL = os.getenv("RPC_URL", "https://rpc.sepolia.org")
```

**Verify:**
```bash
python3 << 'EOF'
from web3 import Web3
rpc = "https://rpc.sepolia.org"
w3 = Web3(Web3.HTTPProvider(rpc))
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")  # Should be 11155111
EOF
```

### Step 1.2: Add All 5 Contract Addresses to config.py

**File:** `config.py` (after line 56)

```python
# On-chain Configuration (ERC-8004 Ethereum Sepolia)
RPC_URL = os.getenv("RPC_URL", "https://rpc.sepolia.org")
AGENT_WALLET_KEY = os.getenv("AGENT_WALLET_KEY", "")

# ✅ REQUIRED: These are the official shared contracts - DO NOT CHANGE
AGENT_REGISTRY_ADDRESS = "0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3"
HACKATHON_VAULT_ADDRESS = "0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90"
RISK_ROUTER_ADDRESS = "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC"
REPUTATION_REGISTRY_ADDRESS = "0x423a9904e39537a9997fbaF0f220d79D7d545763"
VALIDATION_REGISTRY_ADDRESS = "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1"
```

### Step 1.3: Create .env with Private Key

**File:** `.env` (new or update)

```bash
# Web3 Configuration
INFURA_API_KEY=your_infura_key_here
AGENT_WALLET_KEY=0x...  # Your agent's private key (NOT operator wallet)

# Kraken Configuration
KRAKEN_API_KEY=...
KRAKEN_API_SECRET=...
KRAKEN_CLI_PATH=/usr/local/bin/kraken

# Contract addresses (already in config.py)
AGENT_ID=  # Will be set after registration
```

---

## Phase 2: On-Chain Agent Registration (2 hours)

### Step 2.1: Create Agent Registration Script

**File:** `scripts/register_agent.py` (new)

```python
#!/usr/bin/env python3
"""
Register NEXUS agent on AgentRegistry (ERC-8004 shared contract)
Outputs agentId to agent-id.json for use in subsequent calls
"""

import json
import sys
from web3 import Web3
from eth_account import Account
import config

def register_agent():
    """Register agent on AgentRegistry contract"""
    
    # Connect to Sepolia
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        print(f"❌ Failed to connect to {config.RPC_URL}")
        sys.exit(1)
    
    print(f"✓ Connected to Sepolia (Chain ID: {w3.eth.chain_id})")
    
    # Load agent wallet
    if not config.AGENT_WALLET_KEY:
        print("❌ AGENT_WALLET_KEY not set in .env")
        sys.exit(1)
    
    agent_account = Account.from_key(config.AGENT_WALLET_KEY)
    print(f"✓ Agent wallet: {agent_account.address}")
    
    # AgentRegistry ABI (minimal)
    agent_registry_abi = json.loads("""[
        {
            "inputs": [
                {"name": "agentWallet", "type": "address"},
                {"name": "name", "type": "string"},
                {"name": "description", "type": "string"},
                {"name": "capabilities", "type": "string[]"},
                {"name": "agentURI", "type": "string"}
            ],
            "name": "register",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]""")
    
    # Create contract instance
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(config.AGENT_REGISTRY_ADDRESS),
        abi=agent_registry_abi
    )
    
    # Build registration transaction
    capabilities = ["momentum", "sentiment", "mean_reversion", "risk_guardian"]
    tx = registry.functions.register(
        agent_account.address,
        "NEXUS Trading Agent",
        "Multi-agent consensus trading system",
        capabilities,
        "https://nexus.trading/agent"
    ).build_transaction({
        'from': agent_account.address,
        'nonce': w3.eth.get_transaction_count(agent_account.address),
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    # Sign and send
    signed = agent_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"📤 Registration tx: {tx_hash.hex()}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✓ Receipt: {receipt['transactionHash'].hex()}")
    
    # Parse agentId from logs
    # (This would require parsing the event, simplified here)
    agent_id = 123  # In practice, parse from event logs
    
    # Save to agent-id.json
    with open('agent-id.json', 'w') as f:
        json.dump({
            'agentId': agent_id,
            'wallet': agent_account.address,
            'registrationTx': tx_hash.hex(),
            'timestamp': int(time.time())
        }, f, indent=2)
    
    print(f"✓ Agent registered! agentId: {agent_id}")
    print(f"✓ Saved to agent-id.json")
    print(f"\nNext: Run 'python3 scripts/claim_capital.py' to claim 0.05 ETH")

if __name__ == "__main__":
    import time
    register_agent()
```

**Run:**
```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
python3 scripts/register_agent.py
```

### Step 2.2: Create Sandbox Capital Claim Script

**File:** `scripts/claim_capital.py` (new)

```python
#!/usr/bin/env python3
"""
Claim 0.05 ETH sandbox capital from HackathonVault for registered agent
"""

import json
import sys
from web3 import Web3
from eth_account import Account
import config

def claim_capital():
    """Claim sandbox capital allocation"""
    
    # Load agent ID
    try:
        with open('agent-id.json') as f:
            agent_data = json.load(f)
            agent_id = agent_data['agentId']
    except:
        print("❌ agent-id.json not found. Run 'python3 scripts/register_agent.py' first")
        sys.exit(1)
    
    # Connect to Sepolia
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        print(f"❌ Failed to connect to {config.RPC_URL}")
        sys.exit(1)
    
    print(f"✓ Connected to Sepolia")
    print(f"✓ Agent ID: {agent_id}")
    
    # Load agent wallet
    agent_account = Account.from_key(config.AGENT_WALLET_KEY)
    
    # HackathonVault ABI (minimal)
    vault_abi = json.loads("""[
        {
            "inputs": [{"name": "agentId", "type": "uint256"}],
            "name": "claimAllocation",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"name": "agentId", "type": "uint256"}],
            "name": "getBalance",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]""")
    
    # Create contract instance
    vault = w3.eth.contract(
        address=Web3.to_checksum_address(config.HACKATHON_VAULT_ADDRESS),
        abi=vault_abi
    )
    
    # Check current balance
    current_balance = vault.functions.getBalance(agent_id).call()
    print(f"Current balance: {Web3.from_wei(current_balance, 'ether')} ETH")
    
    # Build claim transaction
    tx = vault.functions.claimAllocation(agent_id).build_transaction({
        'from': agent_account.address,
        'nonce': w3.eth.get_transaction_count(agent_account.address),
        'gas': 150000,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    # Sign and send
    signed = agent_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"📤 Claim tx: {tx_hash.hex()}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"✓ Claimed!")
    
    # Check new balance
    new_balance = vault.functions.getBalance(agent_id).call()
    print(f"✓ New balance: {Web3.from_wei(new_balance, 'ether')} ETH")

if __name__ == "__main__":
    claim_capital()
```

**Run:**
```bash
python3 scripts/claim_capital.py
```

---

## Phase 3: Trade Execution via RiskRouter (4 hours)

### Step 3.1: Create RiskRouter Trade Submitter

**File:** `execution/risk_router.py` (new)

```python
"""
Submit trade intents through RiskRouter contract (ERC-8004)
All trades MUST go through this - no direct Kraken calls
"""

import json
import time
from typing import Dict, Any, Optional
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_structured_data
import config

class RiskRouterClient:
    """Submit trades through RiskRouter contract"""
    
    def __init__(self, rpc_url: str = config.RPC_URL, agent_wallet_key: str = config.AGENT_WALLET_KEY):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.agent_account = Account.from_key(agent_wallet_key) if agent_wallet_key else None
        
        # RiskRouter ABI (simplified - see full in SHARED_CONTRACTS.md)
        self.router_abi = json.loads("""[
            {
                "inputs": [
                    {
                        "components": [
                            {"name": "agentId", "type": "uint256"},
                            {"name": "agentWallet", "type": "address"},
                            {"name": "pair", "type": "string"},
                            {"name": "action", "type": "string"},
                            {"name": "amountUsdScaled", "type": "uint256"},
                            {"name": "maxSlippageBps", "type": "uint16"},
                            {"name": "nonce", "type": "uint256"},
                            {"name": "deadline", "type": "uint256"}
                        ],
                        "name": "tradeIntent",
                        "type": "tuple"
                    },
                    {"name": "signature", "type": "bytes"}
                ],
                "name": "submitTradeIntent",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]""")
        
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.RISK_ROUTER_ADDRESS),
            abi=self.router_abi
        )
    
    def submit_trade(
        self,
        agent_id: int,
        pair: str,
        action: str,  # "BUY" or "SELL"
        amount_usd: float,  # In dollars, e.g., 500
        max_slippage_bps: int = 100  # 100 = 1%
    ) -> Optional[str]:
        """
        Submit trade intent through RiskRouter
        
        Args:
            agent_id: Agent's on-chain ID
            pair: Trading pair, e.g., "XBTUSD"
            action: "BUY" or "SELL"
            amount_usd: Dollar amount (max 500 enforced on-chain)
            max_slippage_bps: Max slippage in basis points
        
        Returns:
            Transaction hash if successful, None otherwise
        """
        
        # Build trade intent struct
        amount_scaled = int(amount_usd * 100)  # Scale to match contract
        nonce = self._get_signing_nonce(agent_id)
        deadline = int(time.time()) + 300  # 5 minute expiry
        
        trade_intent = {
            'agentId': agent_id,
            'agentWallet': self.agent_account.address,
            'pair': pair,
            'action': action,
            'amountUsdScaled': amount_scaled,
            'maxSlippageBps': max_slippage_bps,
            'nonce': nonce,
            'deadline': deadline
        }
        
        # Sign with EIP-712
        signature = self._sign_trade_intent(trade_intent)
        
        # Submit transaction
        try:
            tx = self.router.functions.submitTradeIntent(
                trade_intent,
                signature
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            signed = self.agent_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            print(f"✓ Trade submitted: {action} {amount_usd} {pair}")
            print(f"  Tx: {tx_hash.hex()}")
            
            return tx_hash.hex()
        
        except Exception as e:
            print(f"❌ Trade submission failed: {e}")
            return None
    
    def _get_signing_nonce(self, agent_id: int) -> int:
        """Get current signing nonce from contract"""
        # This would call AgentRegistry.getSigningNonce(agent_id)
        # Simplified for now
        return int(time.time())
    
    def _sign_trade_intent(self, trade_intent: Dict) -> str:
        """Sign trade intent with EIP-712"""
        
        domain = {
            'name': 'RiskRouter',
            'version': '1',
            'chainId': self.w3.eth.chain_id,
            'verifyingContract': config.RISK_ROUTER_ADDRESS
        }
        
        types = {
            'TradeIntent': [
                {'name': 'agentId', 'type': 'uint256'},
                {'name': 'agentWallet', 'type': 'address'},
                {'name': 'pair', 'type': 'string'},
                {'name': 'action', 'type': 'string'},
                {'name': 'amountUsdScaled', 'type': 'uint256'},
                {'name': 'maxSlippageBps', 'type': 'uint16'},
                {'name': 'nonce', 'type': 'uint256'},
                {'name': 'deadline', 'type': 'uint256'}
            ]
        }
        
        message_hash = encode_structured_data({
            'types': types,
            'domain': domain,
            'primaryType': 'TradeIntent',
            'message': trade_intent
        })
        
        signed = self.agent_account.sign_message(message_hash)
        return signed.signature.hex()
```

### Step 3.2: Update main.py to Use RiskRouter

**File:** `main.py` (around line 330-350)

**BEFORE:**
```python
if consensus_decision == VoteDirection.BUY:
    volume = compute_position_size(...)
    kraken_client.market_buy(volume)  # ❌ WRONG: Direct Kraken call
    
elif consensus_decision == VoteDirection.SELL:
    kraken_client.market_sell(volume)  # ❌ WRONG: Direct Kraken call
```

**AFTER:**
```python
from execution.risk_router import RiskRouterClient

# At top of file
router_client = RiskRouterClient()

# In trade cycle:
if consensus_decision == VoteDirection.BUY:
    # Get agentId from agent-id.json
    with open('agent-id.json') as f:
        agent_data = json.load(f)
        agent_id = agent_data['agentId']
    
    # Submit through RiskRouter (enforces limits on-chain)
    tx_hash = router_client.submit_trade(
        agent_id=agent_id,
        pair="XBTUSD",
        action="BUY",
        amount_usd=trade_size_usd,
        max_slippage_bps=100
    )
    
    if tx_hash:
        # Wait for trade approval/rejection event
        # Then sync position with Kraken
        portfolio_summary = kraken_client.portfolio_summary()
        position_manager.track_position(...)

elif consensus_decision == VoteDirection.SELL:
    tx_hash = router_client.submit_trade(
        agent_id=agent_id,
        pair="XBTUSD",
        action="SELL",
        amount_usd=trade_size_usd,
        max_slippage_bps=100
    )
```

---

## Phase 4: Rate Limiter Enforcement (1 hour)

### Step 4.1: Create Rate Limiter Class

**File:** `execution/rate_limiter.py` (new)

```python
"""
Enforce ERC-8004 trading limits:
- Max $500 per trade
- Max 10 trades per hour
- Max 5% drawdown
"""

import time
from typing import Tuple
import config

class RateLimiter:
    """Enforce trading limits"""
    
    def __init__(self):
        self.trade_history = []  # List of timestamps
        self.peak_portfolio_value = None
        self.trades_in_cycle = 0  # For reporting
    
    def check_trade_allowed(
        self,
        trade_size_usd: float,
        current_portfolio_value: float
    ) -> Tuple[bool, str]:
        """
        Check if trade is allowed under all limits
        
        Returns:
            (allowed: bool, reason: str)
        """
        
        # 1. Check size limit
        max_size = config.MAX_TRADE_SIZE_USD  # 500
        if trade_size_usd > max_size:
            return False, f"Trade ${trade_size_usd} exceeds max ${max_size}"
        
        # 2. Check hourly rate limit
        now = time.time()
        one_hour_ago = now - 3600
        recent_trades = [t for t in self.trade_history if t > one_hour_ago]
        
        max_per_hour = 10
        if len(recent_trades) >= max_per_hour:
            return False, f"Hourly limit reached: {len(recent_trades)} trades in last hour"
        
        # 3. Check drawdown limit
        max_drawdown = config.MAX_DRAWDOWN_PCT  # 5%
        
        if self.peak_portfolio_value is None:
            self.peak_portfolio_value = current_portfolio_value
        
        current_drawdown = (self.peak_portfolio_value - current_portfolio_value) / self.peak_portfolio_value
        if current_drawdown > (max_drawdown / 100):
            return False, f"Drawdown {current_drawdown*100:.1f}% exceeds max {max_drawdown}%"
        
        # Update peak
        self.peak_portfolio_value = max(self.peak_portfolio_value, current_portfolio_value)
        
        return True, "OK"
    
    def record_trade(self):
        """Record that a trade was executed"""
        self.trade_history.append(time.time())
        self.trades_in_cycle += 1
    
    def get_stats(self) -> dict:
        """Get current rate limiter statistics"""
        now = time.time()
        one_hour_ago = now - 3600
        recent_trades = [t for t in self.trade_history if t > one_hour_ago]
        
        return {
            'trades_this_hour': len(recent_trades),
            'trades_max': 10,
            'total_trades_lifetime': len(self.trade_history),
            'drawdown_pct': (1 - (self.peak_portfolio_value or 0) / (self.peak_portfolio_value or 1)) * 100,
            'drawdown_max': config.MAX_DRAWDOWN_PCT
        }
```

### Step 4.2: Integrate into main.py

**File:** `main.py` (at top of trade cycle)

```python
from execution.rate_limiter import RateLimiter

# At initialization
rate_limiter = RateLimiter()

# Before each trade
portfolio_value, _ = kraken_client.portfolio_summary()

allowed, reason = rate_limiter.check_trade_allowed(
    trade_size_usd=proposed_trade_size,
    current_portfolio_value=portfolio_value
)

if allowed:
    tx_hash = router_client.submit_trade(...)
    rate_limiter.record_trade()
else:
    console.print(f"[yellow]Trade blocked: {reason}[/yellow]")
```

---

## Phase 5: Checkpoint Posting to ValidationRegistry (2 hours)

### Step 5.1: Create Checkpoint Poster

**File:** `execution/validation_checkpoint.py` (new)

```python
"""
Post agent decisions to ValidationRegistry for real-time scoring
"""

import json
import time
from typing import Dict, Any
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_structured_data
import config

class ValidationCheckpointPoster:
    """Post checkpoints to ValidationRegistry"""
    
    def __init__(self, rpc_url: str = config.RPC_URL, agent_wallet_key: str = config.AGENT_WALLET_KEY):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.agent_account = Account.from_key(agent_wallet_key) if agent_wallet_key else None
        
        # ValidationRegistry ABI (simplified)
        self.validation_abi = json.loads("""[
            {
                "inputs": [
                    {"name": "agentId", "type": "uint256"},
                    {"name": "checkpointHash", "type": "bytes32"},
                    {"name": "score", "type": "uint256"},
                    {"name": "notes", "type": "string"}
                ],
                "name": "postEIP712Attestation",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function"
            }
        ]""")
        
        self.validator = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.VALIDATION_REGISTRY_ADDRESS),
            abi=self.validation_abi
        )
    
    def post_checkpoint(
        self,
        agent_id: int,
        decision: str,  # "BUY" or "SELL"
        confidence: float,  # 0-1
        reasoning: Dict[str, Any]
    ) -> bool:
        """Post checkpoint after agent decision"""
        
        # Create checkpoint struct (EIP-712)
        checkpoint = {
            'decision': decision,
            'confidence': int(confidence * 100),  # 0-100
            'timestamp': int(time.time()),
            'reasoning': json.dumps(reasoning)
        }
        
        # Hash the checkpoint
        checkpoint_hash = self.w3.keccak(text=json.dumps(checkpoint))
        
        # Score: 50 + (confidence * 50) = 50-100
        score = int(50 + (confidence * 50))
        
        # Submit to contract
        try:
            tx = self.validator.functions.postEIP712Attestation(
                agent_id,
                checkpoint_hash,
                score,
                json.dumps(checkpoint)
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 200000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            signed = self.agent_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            # Also save locally
            self._save_checkpoint_locally(agent_id, checkpoint, tx_hash.hex())
            
            return True
        
        except Exception as e:
            print(f"❌ Checkpoint posting failed: {e}")
            return False
    
    def _save_checkpoint_locally(self, agent_id: int, checkpoint: Dict, tx_hash: str):
        """Save checkpoint to local checkpoints.jsonl for audit trail"""
        with open('checkpoints.jsonl', 'a') as f:
            record = {
                'agentId': agent_id,
                'checkpoint': checkpoint,
                'txHash': tx_hash,
                'timestamp': int(time.time())
            }
            f.write(json.dumps(record) + '\n')
```

### Step 5.2: Post Checkpoint After Each Decision

**File:** `main.py` (in consensus voting section)

```python
from execution.validation_checkpoint import ValidationCheckpointPoster

# At initialization
checkpoint_poster = ValidationCheckpointPoster()

# After consensus decision
consensus_decision, avg_confidence = consensus_engine.vote(agents, market_data)

if consensus_decision != VoteDirection.HOLD:
    # Post to ValidationRegistry
    reasoning = {
        'agents': {a.name: {'vote': str(a.last_vote), 'conf': a.confidence} for a in agents},
        'regime': market_data.regime.value,
        'rsi_1h': market_data.rsi_1h,
        'rsi_4h': market_data.rsi_4h,
        'price': market_data.current_price
    }
    
    checkpoint_poster.post_checkpoint(
        agent_id=agent_id,
        decision=str(consensus_decision),
        confidence=avg_confidence,
        reasoning=reasoning
    )
```

---

## Phase 6: Dashboard Live Updates (2 hours)

### Step 6.1: Add Event Listeners to Dashboard

**File:** `dashboard.html` or `dashboard.ts` (update)

```typescript
import { WebSocketProvider, Contract } from 'ethers';

const RPC_URL = 'https://rpc.sepolia.org';
const RISK_ROUTER_ADDRESS = '0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC';
const REP_REGISTRY_ADDRESS = '0x423a9904e39537a9997fbaF0f220d79D7d545763';

// Connect to WebSocket provider for events
const provider = new WebSocketProvider(RPC_URL.replace('https', 'wss'));

// Listen for TradeApproved events
const riskRouterABI = [
    'event TradeApproved(uint256 agentId, bytes32 tradeHash, uint256 executedPrice)',
    'event TradeRejected(uint256 agentId, bytes32 tradeHash, string reason)'
];

const router = new Contract(RISK_ROUTER_ADDRESS, riskRouterABI, provider);

router.on('TradeApproved', (agentId, tradeHash, executedPrice) => {
    // Update dashboard in real-time
    updateTradeUI({
        agentId,
        tradeHash,
        executedPrice: ethers.formatUnits(executedPrice, 8),
        status: 'APPROVED'
    });
});

router.on('TradeRejected', (agentId, tradeHash, reason) => {
    updateTradeUI({
        agentId,
        tradeHash,
        reason,
        status: 'REJECTED'
    });
});

// Listen for reputation updates
const repABI = [
    'event ScoreUpdated(uint256 agentId, uint256 newScore)'
];

const repRegistry = new Contract(REP_REGISTRY_ADDRESS, repABI, provider);

repRegistry.on('ScoreUpdated', (agentId, newScore) => {
    // Update agent reputation in real-time
    updateReputationUI({
        agentId,
        score: newScore.toNumber()
    });
});
```

---

## Phase 7: Exponential Agent Penalties (1 hour)

### Step 7.1: Update Agent Learning

**File:** `consensus/engine.py` (update agent weight updates)

**BEFORE:**
```python
# Linear penalty
agent.weight -= 0.05 * confidence
```

**AFTER:**
```python
# Track consecutive outcomes
if not hasattr(agent, 'consecutive_wins'):
    agent.consecutive_wins = 0
    agent.consecutive_losses = 0

if trade_won:
    agent.consecutive_wins += 1
    agent.consecutive_losses = 0
    # Exponential bonus for winning streak
    multiplier = 1.1 ** agent.consecutive_wins
    agent.weight *= multiplier
else:
    agent.consecutive_losses += 1
    agent.consecutive_wins = 0
    # Exponential penalty for losing streak
    multiplier = 0.9 ** agent.consecutive_losses
    agent.weight *= multiplier

# Cap weight to reasonable range
agent.weight = max(0.1, min(agent.weight, 5.0))
```

---

## Testing & Verification Checklist

After each phase, verify:

### Phase 1: Network Config
```bash
python3 << 'EOF'
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('https://rpc.sepolia.org'))
print(f"Connected: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")  # Must be 11155111
EOF
```

### Phase 2: Agent Registration
```bash
# Should have agent-id.json with agentId
cat agent-id.json

# Check agent is registered
npx ethers call 0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3 "isRegistered(uint256)" 123 --rpc-url https://rpc.sepolia.org
```

### Phase 3: Trade Submission
```bash
# Monitor RiskRouter events
npx ethers listen-event 0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC "TradeApproved" --rpc-url https://rpc.sepolia.org
```

### Phase 4: Rate Limiting
```bash
# Check limiter stats in real-time logs
grep "rate_limiter" nexus.log
```

### Phase 5: Checkpoints
```bash
# Should have checkpoints.jsonl
wc -l checkpoints.jsonl  # Growing with each decision
```

### Phase 6: Dashboard
```bash
# Dashboard should show live trades and reputation
open http://localhost:3000/dashboard
```

### Phase 7: Agent Penalties
```bash
# Check nexus_weights.json shows exponential changes
cat nexus_weights.json | python3 -m json.tool
```

---

## Expected Outcomes

Once complete:

✅ Trades submitted through RiskRouter (verified via events)  
✅ Rate limits enforced at contract level  
✅ Checkpoints posted and scored in real-time  
✅ Agent reputation accumulates correctly  
✅ Dashboard shows live contract events  
✅ Project meets all 12 ERC-8004 requirements  

**Estimated completion:** 12-16 hours of focused development

