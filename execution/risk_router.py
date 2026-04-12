"""
Submit trades through RiskRouter contract (ERC-8004)
All trades MUST go through this - no direct Kraken calls
"""

import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_structured_data
import config

logger = logging.getLogger(__name__)

class RiskRouterClient:
    """Submit trades through RiskRouter contract with full EIP-712 signing"""
    
    def __init__(self, rpc_url: str = None, agent_wallet_key: str = None):
        """
        Initialize RiskRouter client
        
        Args:
            rpc_url: RPC endpoint (uses config.RPC_URL if not provided)
            agent_wallet_key: Agent wallet private key (uses config.AGENT_WALLET_KEY if not provided)
        """
        self.rpc_url = rpc_url or config.RPC_URL
        self.agent_wallet_key = agent_wallet_key or config.AGENT_WALLET_KEY
        
        # Connect to blockchain
        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise ConnectionError(f"Cannot connect to {self.rpc_url}")
        
        # Load agent account
        if not self.agent_wallet_key:
            raise ValueError("AGENT_WALLET_KEY not configured")
        
        try:
            self.agent_account = Account.from_key(self.agent_wallet_key)
        except Exception as e:
            raise ValueError(f"Invalid private key: {e}")
        
        # RiskRouter contract
        self.router_address = Web3.to_checksum_address(config.RISK_ROUTER_ADDRESS)
        
        # Minimal RiskRouter ABI (submitTradeIntent function)
        self.router_abi = [
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
        ]
        
        self.router = self.w3.eth.contract(
            address=self.router_address,
            abi=self.router_abi
        )
        
        logger.info(f"✓ RiskRouter initialized: {self.router_address}")
        logger.info(f"✓ Agent wallet: {self.agent_account.address}")
    
    def submit_trade(
        self,
        agent_id: int,
        pair: str,
        action: str,
        amount_usd: float,
        max_slippage_bps: int = 100
    ) -> Optional[str]:
        """
        Submit trade intent through RiskRouter
        
        RiskRouter enforces:
        - Max $500 per trade
        - Max 10 trades per hour
        - Max 5% drawdown
        
        Args:
            agent_id: Agent's on-chain ID
            pair: Trading pair (e.g., "XBTUSD")
            action: "BUY" or "SELL"
            amount_usd: Dollar amount (max 500 enforced on-chain)
            max_slippage_bps: Max slippage in basis points (100 = 1%)
        
        Returns:
            Transaction hash if successful, None otherwise
        """
        
        # Build trade intent struct
        amount_scaled = int(amount_usd * 100)  # Scale to match contract
        nonce = int(time.time())
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
        
        logger.info(f"\n📝 Building trade intent:")
        logger.info(f"   Agent ID: {agent_id}")
        logger.info(f"   Action: {action} ${amount_usd}")
        logger.info(f"   Pair: {pair}")
        logger.info(f"   Max slippage: {max_slippage_bps / 100}%")
        
        # Sign with EIP-712
        try:
            signature = self._sign_trade_intent(trade_intent)
            logger.info(f"✓ Trade intent signed")
        except Exception as e:
            logger.error(f"❌ Signing failed: {e}")
            return None
        
        # Submit transaction
        try:
            logger.info(f"\n🔗 Submitting to RiskRouter...")
            
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
            
            logger.info(f"✓ Transaction built (gas: {tx['gas']})")
            
            # Sign and send
            signed = self.agent_account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.rawTransaction)
            
            logger.info(f"✓ Transaction submitted")
            logger.info(f"   Hash: {tx_hash.hex()}")
            logger.info(f"   View: https://sepolia.etherscan.io/tx/{tx_hash.hex()}")
            
            return tx_hash.hex()
        
        except Exception as e:
            logger.error(f"❌ Trade submission failed: {e}")
            return None
    
    def _sign_trade_intent(self, trade_intent: Dict) -> str:
        """Sign trade intent with EIP-712"""
        
        domain = {
            'name': 'RiskRouter',
            'version': '1',
            'chainId': self.w3.eth.chain_id,
            'verifyingContract': self.router_address
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
        
        try:
            message_hash = encode_structured_data({
                'types': types,
                'domain': domain,
                'primaryType': 'TradeIntent',
                'message': trade_intent
            })
            
            signed = self.agent_account.sign_message(message_hash)
            return signed.signature.hex()
        except Exception as e:
            logger.error(f"EIP-712 signing failed: {e}")
            raise
    
    def get_chain_id(self) -> int:
        """Get current chain ID"""
        return self.w3.eth.chain_id
    
    def is_connected(self) -> bool:
        """Check if connected to blockchain"""
        return self.w3.is_connected()


def create_risk_router_client() -> RiskRouterClient:
    """Factory function to create RiskRouter client"""
    try:
        return RiskRouterClient()
    except Exception as e:
        logger.error(f"Failed to create RiskRouter client: {e}")
        return None
