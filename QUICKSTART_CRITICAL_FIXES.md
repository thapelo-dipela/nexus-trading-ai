# ERC-8004 Quick-Start Fixes

**Priority:** CRITICAL - Do These First Before Anything Else  
**Estimated Time:** 2 hours total  
**Outcome:** Project becomes competition-eligible

---

## The 3 Critical Issues

Your project fails on these 3 core requirements:

1. ❌ **Wrong Network** - RPC points to Base instead of Ethereum Sepolia
2. ❌ **No Agent Registration** - Agent has no on-chain identity
3. ❌ **Trades Bypass RiskRouter** - Direct to Kraken instead of smart contract

All other work depends on fixing these first.

---

## Fix #1: Network Configuration (15 minutes)

### Step 1: Fix config.py

Replace line 47 in `config.py`:

```python
# WRONG (current)
RPC_URL = os.getenv("RPC_URL", "https://sepolia.base.org")

# CORRECT (change to)
RPC_URL = os.getenv("RPC_URL", "https://rpc.sepolia.org")
```

### Step 2: Add Contract Addresses

Add after line 56 in `config.py`:

```python
# On-chain Configuration (ERC-8004 Ethereum Sepolia)
AGENT_REGISTRY_ADDRESS = "0x97b07dDc405B0c28B17559aFFE63BdB3632d0ca3"
HACKATHON_VAULT_ADDRESS = "0x0E7CD8ef9743FEcf94f9103033a044caBD45fC90"
RISK_ROUTER_ADDRESS = "0xd6A6952545FF6E6E6681c2d15C59f9EB8F40FdBC"
REPUTATION_REGISTRY_ADDRESS = "0x423a9904e39537a9997fbaF0f220d79D7d545763"
VALIDATION_REGISTRY_ADDRESS = "0x92bF63E5C7Ac6980f237a7164Ab413BE226187F1"
```

### Step 3: Verify

```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai

python3 << 'EOF'
from web3 import Web3
import config

w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
if w3.is_connected() and w3.eth.chain_id == 11155111:
    print("✓ Connected to Sepolia!")
    print(f"  Chain ID: {w3.eth.chain_id}")
else:
    print("✗ Still on wrong network")
    print(f"  Chain ID: {w3.eth.chain_id}")
EOF
```

Expected output:
```
✓ Connected to Sepolia!
  Chain ID: 11155111
```

---

## Fix #2: Agent Registration (30 minutes)

### Step 1: Create .env with Private Key

Create `.env` file in project root:

```bash
# Agent wallet private key (NOT operator wallet)
# This must be different from your operator wallet
AGENT_WALLET_KEY=0x...your_private_key...

# Kraken credentials (already have these)
KRAKEN_API_KEY=...
KRAKEN_API_SECRET=...
```

**IMPORTANT:** The `AGENT_WALLET_KEY` is the private key that signs trade intents. Keep it secure!

### Step 2: Create Registration Script

Create `scripts/register_agent.py`:

```python
#!/usr/bin/env python3
"""Register NEXUS agent on AgentRegistry"""

import json
import sys
import time
from web3 import Web3
from eth_account import Account
import config

def main():
    # Connect to Sepolia
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    if not w3.is_connected():
        print(f"❌ Cannot connect to {config.RPC_URL}")
        sys.exit(1)
    
    print(f"✓ Connected to Sepolia (Chain ID: {w3.eth.chain_id})")
    
    # Load agent wallet
    if not config.AGENT_WALLET_KEY:
        print("❌ AGENT_WALLET_KEY not set in .env")
        sys.exit(1)
    
    agent_account = Account.from_key(config.AGENT_WALLET_KEY)
    print(f"✓ Agent wallet: {agent_account.address}")
    
    # Check balance (need gas for registration)
    balance = w3.eth.get_balance(agent_account.address)
    balance_eth = Web3.from_wei(balance, 'ether')
    print(f"  Balance: {balance_eth:.4f} ETH")
    
    if balance_eth < 0.01:
        print("⚠️  WARNING: Low balance (need ~0.01 ETH for gas)")
        print("   Send test ETH from https://sepoliafaucet.com to continue")
        sys.exit(1)
    
    # AgentRegistry ABI
    abi = json.loads("""[{
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
    }]""")
    
    # Create contract instance
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(config.AGENT_REGISTRY_ADDRESS),
        abi=abi
    )
    
    print("\n📤 Registering agent on AgentRegistry...")
    
    # Build transaction
    tx = registry.functions.register(
        agent_account.address,
        "NEXUS Trading Agent",
        "Multi-agent consensus trading system",
        ["momentum", "sentiment", "mean_reversion", "risk_guardian"],
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
    print(f"  Tx hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("  Waiting for confirmation (30-60 seconds)...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] != 1:
        print("❌ Registration failed!")
        sys.exit(1)
    
    print("✓ Registration confirmed!")
    
    # Parse agentId from logs (simplified - would need event parsing)
    # For now, save placeholder
    agent_id = 1  # In production, parse from event
    
    # Save to agent-id.json
    agent_data = {
        'agentId': agent_id,
        'wallet': agent_account.address,
        'registrationTx': tx_hash.hex(),
        'timestamp': int(time.time())
    }
    
    with open('agent-id.json', 'w') as f:
        json.dump(agent_data, f, indent=2)
    
    print(f"\n✓ Agent registered!")
    print(f"  Agent ID: {agent_id}")
    print(f"  Saved to agent-id.json")
    print(f"\n📋 Next steps:")
    print(f"  1. Update agent-id.json with actual agentId (parse from Etherscan)")
    print(f"  2. Run: python3 scripts/claim_capital.py")

if __name__ == "__main__":
    main()
```

### Step 3: Run Registration

```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai
python3 scripts/register_agent.py
```

You should see:
```
✓ Connected to Sepolia (Chain ID: 11155111)
✓ Agent wallet: 0x...
  Balance: 0.0234 ETH
📤 Registering agent on AgentRegistry...
  Tx hash: 0x...
  Waiting for confirmation...
✓ Registration confirmed!
✓ Agent registered!
  Agent ID: 1
  Saved to agent-id.json
```

### Step 4: Claim Sandbox Capital

Create `scripts/claim_capital.py`:

```python
#!/usr/bin/env python3
"""Claim 0.05 ETH sandbox capital"""

import json
from web3 import Web3
from eth_account import Account
import config

def main():
    # Load agent ID
    with open('agent-id.json') as f:
        agent_data = json.load(f)
        agent_id = agent_data['agentId']
    
    # Connect
    w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
    agent_account = Account.from_key(config.AGENT_WALLET_KEY)
    
    print(f"📤 Claiming capital for agent {agent_id}...")
    
    # HackathonVault ABI
    abi = json.loads("""[{
        "inputs": [{"name": "agentId", "type": "uint256"}],
        "name": "claimAllocation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }]""")
    
    vault = w3.eth.contract(
        address=Web3.to_checksum_address(config.HACKATHON_VAULT_ADDRESS),
        abi=abi
    )
    
    # Build and send
    tx = vault.functions.claimAllocation(agent_id).build_transaction({
        'from': agent_account.address,
        'nonce': w3.eth.get_transaction_count(agent_account.address),
        'gas': 150000,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    signed = agent_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    
    print(f"  Tx hash: {tx_hash.hex()}")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    
    if receipt['status'] == 1:
        print("✓ Claimed 0.05 ETH sandbox capital!")
    else:
        print("❌ Claim failed")

if __name__ == "__main__":
    main()
```

Run it:
```bash
python3 scripts/claim_capital.py
```

---

## Fix #3: Route Trades Through RiskRouter (1.5 hours)

### Step 1: Create RiskRouter Client

Create `execution/risk_router.py`:

```python
"""Submit trades through RiskRouter contract"""

import json
import time
from typing import Optional
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_structured_data
import config

class RiskRouterClient:
    """Submit trades through RiskRouter"""
    
    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
        self.agent_account = Account.from_key(config.AGENT_WALLET_KEY)
        
        abi = json.loads("""[{
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
        }]""")
        
        self.router = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.RISK_ROUTER_ADDRESS),
            abi=abi
        )
    
    def submit_trade(
        self,
        agent_id: int,
        action: str,  # "BUY" or "SELL"
        amount_usd: float
    ) -> Optional[str]:
        """
        Submit trade through RiskRouter (enforces limits on-chain)
        """
        
        trade_intent = {
            'agentId': agent_id,
            'agentWallet': self.agent_account.address,
            'pair': 'XBTUSD',
            'action': action,
            'amountUsdScaled': int(amount_usd * 100),
            'maxSlippageBps': 100,
            'nonce': int(time.time()),
            'deadline': int(time.time()) + 300
        }
        
        try:
            # Sign and submit (simplified - full EIP-712 in implementation guide)
            tx = self.router.functions.submitTradeIntent(
                trade_intent,
                b''  # Signature would go here
            ).build_transaction({
                'from': self.agent_account.address,
                'nonce': self.w3.eth.get_transaction_count(self.agent_account.address),
                'gas': 300000,
                'gasPrice': self.w3.eth.gas_price,
                'chainId': self.w3.eth.chain_id
            })
            
            signed = self.agent_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            print(f"✓ Trade submitted: {action} ${amount_usd} via RiskRouter")
            print(f"  Tx: {tx_hash.hex()}")
            
            return tx_hash.hex()
        
        except Exception as e:
            print(f"❌ Trade submission failed: {e}")
            return None
```

### Step 2: Update main.py

Find the trade execution section (around line 330-350) and replace:

```python
# BEFORE (WRONG)
if consensus_decision == VoteDirection.BUY:
    kraken_client.market_buy(volume)

# AFTER (CORRECT)
from execution.risk_router import RiskRouterClient

router = RiskRouterClient()

if consensus_decision == VoteDirection.BUY:
    # Load agent ID
    with open('agent-id.json') as f:
        agent_id = json.load(f)['agentId']
    
    # Submit through RiskRouter (enforces limits)
    tx_hash = router.submit_trade(agent_id, "BUY", trade_size_usd)
    if tx_hash:
        # Wait for approval event, then sync with Kraken
        # ... position tracking code ...
```

### Step 3: Verify

```bash
cd /Users/thapelodipela/Desktop/nexus-trading-ai

# Check that all files are in place
ls -1 config.py agent-id.json scripts/register_agent.py scripts/claim_capital.py execution/risk_router.py

# Test RPC connection
python3 << 'EOF'
import config
from web3 import Web3
w3 = Web3(Web3.HTTPProvider(config.RPC_URL))
print(f"RPC OK: {w3.is_connected()}")
print(f"Chain: {w3.eth.chain_id}")
print(f"Contracts loaded:")
print(f"  AgentRegistry: {config.AGENT_REGISTRY_ADDRESS}")
print(f"  RiskRouter: {config.RISK_ROUTER_ADDRESS}")
EOF
```

---

## Verification Checklist

After all 3 fixes:

- [ ] RPC points to chain 11155111 (Sepolia)
- [ ] All 5 contract addresses in config.py
- [ ] agent-id.json exists with agentId
- [ ] Agent can be looked up on AgentRegistry (Etherscan)
- [ ] Sandbox capital claimed (0.05 ETH received)
- [ ] Trade submission goes through RiskRouter
- [ ] Trade events visible on contract

---

## Next Steps After These Fixes

1. **Rate Limiter** - Enforce max $500/trade, 10/hour, 5% drawdown
2. **Checkpoints** - Post decisions to ValidationRegistry
3. **Dashboard** - Show live contract events
4. **Penalties** - Exponential agent weight adjustments

See `ERC8004_IMPLEMENTATION_REQUIRED.md` for full details.

---

## Quick Troubleshooting

**Issue:** "Cannot connect to RPC"
```bash
# Verify RPC is reachable
curl https://rpc.sepolia.org -X POST -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}'
```

**Issue:** Registration transaction fails
```bash
# Check gas price is not too low
python3 << 'EOF'
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://rpc.sepolia.org"))
print(f"Gas price: {Web3.from_wei(w3.eth.gas_price, 'gwei')} gwei")
EOF
```

**Issue:** Agent wallet has no balance
- Go to https://sepoliafaucet.com
- Enter your agent wallet address
- Request 0.5 ETH

---

## Time Estimates

- Fix #1 (Network): 15 min
- Fix #2 (Registration): 30 min (includes waiting for tx)
- Fix #3 (RiskRouter): 45 min

**Total: ~2 hours to competition-eligible state**

Then 10-14 more hours for full compliance (checkpoints, rate limiting, penalties, dashboard).

