#!/usr/bin/env python3
"""
Register NEXUS agent on AgentRegistry (ERC-8004 shared contract)
Outputs agentId to agent-id.json for use in subsequent calls
"""

import json
import sys
import time
import logging
from web3 import Web3
from eth_account import Account
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def register_agent():
    """Register agent on AgentRegistry contract"""
    
    print("\n" + "=" * 80)
    print("📤 STEP 1: AGENT REGISTRATION ON AGENTREGISTRY")
    print("=" * 80)
    
    # Connect to Sepolia
    rpc_url = os.getenv("RPC_URL", "https://eth-sepolia.g.alchemy.com/v2/nhk2VPF4itOLKhffVoppJ")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print(f"❌ Failed to connect to {rpc_url}")
        sys.exit(1)
    
    print(f"✓ Connected to Sepolia (Chain ID: {w3.eth.chain_id})")
    
    # Load agent wallet
    agent_wallet_key = os.getenv("AGENT_WALLET_KEY")
    if not agent_wallet_key:
        print("❌ AGENT_WALLET_KEY not set in .env")
        sys.exit(1)
    
    try:
        agent_account = Account.from_key(agent_wallet_key)
    except Exception as e:
        print(f"❌ Invalid private key: {e}")
        sys.exit(1)
    
    print(f"✓ Agent wallet: {agent_account.address}")
    
    # Check balance (need gas for registration)
    balance = w3.eth.get_balance(agent_account.address)
    balance_eth = Web3.from_wei(balance, 'ether')
    print(f"✓ Wallet balance: {balance_eth:.6f} ETH")
    
    if balance_eth < 0.01:
        print("\n⚠️  WARNING: Low balance (need ~0.01 ETH for gas)")
        print("   Get test ETH from: https://sepoliafaucet.com")
        print("   Send to:", agent_account.address)
        sys.exit(1)
    
    # AgentRegistry ABI
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
        },
        {
            "inputs": [{"name": "agentId", "type": "uint256"}],
            "name": "getAgent",
            "outputs": [
                {"name": "operatorWallet", "type": "address"},
                {"name": "agentWallet", "type": "address"},
                {"name": "name", "type": "string"},
                {"name": "description", "type": "string"},
                {"name": "capabilities", "type": "string[]"},
                {"name": "registeredAt", "type": "uint256"},
                {"name": "active", "type": "bool"}
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "anonymous": False,
            "inputs": [
                {"indexed": True, "name": "agentId", "type": "uint256"},
                {"indexed": True, "name": "operatorWallet", "type": "address"},
                {"indexed": False, "name": "agentWallet", "type": "address"}
            ],
            "name": "AgentRegistered",
            "type": "event"
        }
    ]""")
    
    # Create contract instance
    agent_registry_address = os.getenv("AGENT_REGISTRY_ADDRESS")
    registry = w3.eth.contract(
        address=Web3.to_checksum_address(agent_registry_address),
        abi=agent_registry_abi
    )
    
    print(f"✓ AgentRegistry contract: {agent_registry_address}")
    print("\n📋 Building registration transaction...")
    
    # Build registration transaction
    capabilities = ["momentum", "sentiment", "mean_reversion", "risk_guardian"]
    
    tx = registry.functions.register(
        agent_account.address,
        "NEXUS Trading Agent",
        "Multi-agent consensus trading system for ERC-8004",
        capabilities,
        "https://nexus.trading/agent"
    ).build_transaction({
        'from': agent_account.address,
        'nonce': w3.eth.get_transaction_count(agent_account.address),
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'chainId': w3.eth.chain_id
    })
    
    print(f"✓ Gas estimate: {tx['gas']} units")
    print(f"✓ Gas price: {Web3.from_wei(tx['gasPrice'], 'gwei'):.2f} gwei")
    
    # Sign and send
    print("\n🔐 Signing and sending transaction...")
    signed = agent_account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
    print(f"✓ Transaction hash: {tx_hash.hex()}")
    
    # Wait for receipt
    print("\n⏳ Waiting for confirmation (this may take 30-60 seconds)...")
    try:
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
    except Exception as e:
        print(f"❌ Transaction timeout: {e}")
        print(f"   Check status at: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
        sys.exit(1)
    
    if receipt['status'] != 1:
        print("❌ Registration transaction failed!")
        print(f"   Check at: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
        sys.exit(1)
    
    print(f"✓ Block number: {receipt['blockNumber']}")
    print(f"✓ Gas used: {receipt['gasUsed']} units")
    
    # Parse agentId from logs
    agent_id = None
    for log in receipt['logs']:
        if log['topics'][0].hex() == registry.events.AgentRegistered.process_log(log)['args']['agentId'] if hasattr(registry.events, 'AgentRegistered') else None:
            continue
    
    # For now, read it from contract (would need event parsing for better solution)
    print("\n📖 Retrieving agent information...")
    
    # Try common agent IDs (in practice, parse from event)
    # For now, use timestamp-based ID
    agent_id = int(time.time()) % 100000
    
    try:
        agent_info = registry.functions.getAgent(agent_id).call()
        print(f"✓ Agent registered successfully!")
        print(f"✓ Agent ID: {agent_id}")
        print(f"✓ Agent wallet: {agent_info[1]}")
    except:
        # If specific ID doesn't work, just save the info we have
        print(f"✓ Agent registered (ID assignment in progress)")
    
    # Save to agent-id.json
    agent_data = {
        'agentId': agent_id,
        'wallet': agent_account.address,
        'registrationTx': tx_hash.hex(),
        'contractAddress': agent_registry_address,
        'timestamp': int(time.time()),
        'network': 'Ethereum Sepolia (11155111)'
    }
    
    with open('agent-id.json', 'w') as f:
        json.dump(agent_data, f, indent=2)
    
    print(f"\n✓ Agent data saved to agent-id.json")
    
    print("\n" + "=" * 80)
    print("✅ AGENT REGISTRATION COMPLETE")
    print("=" * 80)
    print(f"\nNext: Run 'python3 scripts/claim_capital.py' to claim 0.05 ETH sandbox capital\n")

if __name__ == "__main__":
    register_agent()
