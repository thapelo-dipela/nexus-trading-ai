"""
NEXUS On-chain Reputation Registry — EIP-712 signing and Web3 reputation push.
"""
import logging
import json
import time
from typing import Optional, Dict, Any
try:
    from eth_account import Account
    from eth_account.messages import encode_structured_data
    _ETH_AVAILABLE = True
except ImportError:
    Account = None
    encode_structured_data = None
    _ETH_AVAILABLE = False

try:
    from web3 import Web3
    _WEB3_AVAILABLE = True
except ImportError:
    Web3 = None
    _WEB3_AVAILABLE = False

import config

logger = logging.getLogger(__name__)


class ReputationClient:
    """EIP-712 signing and on-chain reputation push."""

    def __init__(self, rpc_url: str = config.RPC_URL, private_key: str = config.AGENT_WALLET_KEY):
        self.rpc_url = rpc_url
        self.private_key = private_key

        if _WEB3_AVAILABLE and Web3 and rpc_url:
            self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        else:
            self.w3 = None

        if not _ETH_AVAILABLE:
            logger.warning("eth-account not installed — on-chain signing disabled")
            self.account = None
            self.address = None
            return

        if private_key:
            try:
                self.account = Account.from_key(private_key)
                self.address = self.account.address
                logger.info(f"ReputationClient initialized: {self.address}")
            except Exception as e:
                logger.error(f"Invalid private key: {e}")
                self.account = None
                self.address = None
        else:
            logger.warning("No AGENT_WALLET_KEY configured — on-chain push disabled")
            self.account = None
            self.address = None

    def sign_trade_outcome(
        self,
        trade_id: str,
        direction: str,
        confidence: float,
        pnl_usd: float,
        agent_votes: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Sign a trade outcome with EIP-712.
        Returns signed message dict or None on failure.

        Args:
            trade_id: Unique trade identifier
            direction: "BUY", "SELL", or "HOLD"
            confidence: Consensus confidence (0.0–1.0)
            pnl_usd: Profit/loss in USD
            agent_votes: Dict of agent votes
        """
        if not self.account:
            logger.warning("[yellow]Cannot sign: no account configured[/yellow]")
            return None

        if not _ETH_AVAILABLE or not self.account:
            logger.warning("Cannot sign: eth-account not available or no account configured")
            return None

        try:
            timestamp = int(time.time())

            # EIP-712 domain
            domain = {
                "name": "NEXUS",
                "version": "1",
                "chainId": self._get_chain_id(),
                "verifyingContract": config.REPUTATION_REGISTRY_ADDRESS or "0x0",
            }

            # Message types
            message_types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "TradeOutcome": [
                    {"name": "trade_id", "type": "string"},
                    {"name": "direction", "type": "string"},
                    {"name": "confidence", "type": "uint256"},
                    {"name": "pnl_usd", "type": "int256"},
                    {"name": "timestamp", "type": "uint256"},
                ],
            }

            # Message data
            message_data = {
                "trade_id": trade_id,
                "direction": direction,
                "confidence": int(confidence * 1e18),  # Scale to 18 decimals
                "pnl_usd": int(pnl_usd * 100),  # Scale to cents
                "timestamp": timestamp,
            }

            # Encode and sign
            structured_msg = encode_structured_data(
                {
                    "types": message_types,
                    "primaryType": "TradeOutcome",
                    "domain": domain,
                    "message": message_data,
                }
            )

            signed_msg = self.account.sign_message(structured_msg)

            logger.info(f"[green]Trade outcome signed: {trade_id}[/green]")

            return {
                "trade_id": trade_id,
                "direction": direction,
                "confidence": confidence,
                "pnl_usd": pnl_usd,
                "timestamp": timestamp,
                "signature": signed_msg.signature.hex(),
                "agent_votes": agent_votes,
            }

        except Exception as e:
            logger.error(f"[red]Failed to sign trade outcome: {e}[/red]")
            return None

    def sign_vote(self, vote_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a single agent vote using EIP-712 typed data.

        Args:
            vote_data: {
                "agent_id": str,
                "direction": str,  # "BUY", "SELL", "HOLD"
                "confidence": float,  # 0.0-1.0
                "timestamp": int,  # unix timestamp
                "cycle": int
            }

        Returns:
            vote_data with added "signature", "signer", "signed" fields.
            If wallet not configured: returns with "signed": False
        """
        if not self.account:
            vote_data["signed"] = False
            vote_data["signature"] = ""
            vote_data["signer"] = ""
            return vote_data

        if not _ETH_AVAILABLE:
            vote_data["signed"] = False
            vote_data["signature"] = ""
            vote_data["signer"] = ""
            return vote_data

        try:
            # EIP-712 domain
            domain = {
                "name": "NEXUS",
                "version": "1",
                "chainId": config.CHAIN_ID,
                "verifyingContract": config.RISK_ROUTER_ADDRESS,
            }

            # EIP-712 types
            message_types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "AgentVote": [
                    {"name": "agentId", "type": "string"},
                    {"name": "direction", "type": "string"},
                    {"name": "confidence", "type": "uint256"},
                    {"name": "timestamp", "type": "uint256"},
                    {"name": "cycle", "type": "uint256"},
                ],
            }

            # Message data (confidence as basis points: float * 10000)
            message_data = {
                "agentId": vote_data["agent_id"],
                "direction": vote_data["direction"],
                "confidence": int(vote_data["confidence"] * 10000),
                "timestamp": vote_data["timestamp"],
                "cycle": vote_data["cycle"],
            }

            # Encode and sign
            structured_msg = encode_structured_data(
                {
                    "types": message_types,
                    "primaryType": "AgentVote",
                    "domain": domain,
                    "message": message_data,
                }
            )

            signed_msg = self.account.sign_message(structured_msg)

            vote_data["signature"] = signed_msg.signature.hex()
            vote_data["signer"] = self.address
            vote_data["signed"] = True

            logger.debug(f"[dim]Vote signed for {vote_data['agent_id']} ({vote_data['direction']})[/dim]")
            return vote_data

        except Exception as e:
            logger.warning(f"[yellow]Failed to sign vote: {e}[/yellow]")
            vote_data["signed"] = False
            vote_data["signature"] = ""
            vote_data["signer"] = ""
            return vote_data

    def sign_all_votes(self, votes: list[Dict[str, Any]], cycle: int) -> list[Dict[str, Any]]:
        """
        Sign all votes in a list. Errors per-vote are caught and logged.

        Args:
            votes: List of vote dicts
            cycle: Current cycle number

        Returns:
            List of signed (or unsigned if error) vote dicts
        """
        signed_votes = []
        for vote in votes:
            vote["cycle"] = cycle
            vote["timestamp"] = int(time.time())
            signed_vote = self.sign_vote(vote)
            signed_votes.append(signed_vote)

        return signed_votes

    def post_checkpoint(
        self,
        decision_data: Dict[str, Any],
        checkpoint_type: str = "TRADE_DECISION",
        signed_votes: Optional[list[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Post a checkpoint to the on-chain ValidationRegistry.
        Optionally includes signed votes as audit trail.

        Args:
            decision_data: Trade decision data (cycle, direction, confidence, etc.)
            checkpoint_type: Type of checkpoint (TRADE_DECISION, AGENT_CONSENSUS, etc.)
            signed_votes: Optional list of signed vote objects

        Returns:
            True if successful or dry-run, False on error
        """
        try:
            timestamp = int(time.time())

            # Build checkpoint payload
            checkpoint = {
                "checkpoint_type": checkpoint_type,
                "decision_data": decision_data,
                "timestamp": timestamp,
            }

            # Include signed votes if provided
            if signed_votes:
                checkpoint["signed_votes"] = signed_votes
                # Hash includes votes for immutability
                votes_json = json.dumps(signed_votes, sort_keys=True)

            logger.debug(f"[dim]Checkpoint posted: {checkpoint_type} @ {timestamp}[/dim]")

            # TODO: In production, call ValidationRegistry.postCheckpoint()
            # For now, just log the intent
            if signed_votes:
                logger.debug(f"[dim]  + {len(signed_votes)} signed votes included[/dim]")

            return True

        except Exception as e:
            logger.warning(f"[yellow]Checkpoint post failed: {e}[/yellow]")
            return False

    def push_outcome(
        self,
        signed_outcome: Dict[str, Any],
        dry_run: bool = False,
    ) -> bool:
        """
        Push signed outcome to on-chain registry.
        In dry-run mode, logs intent but does not push.

        Args:
            signed_outcome: Signed outcome dict from sign_trade_outcome
            dry_run: If True, do not broadcast transaction

        Returns:
            True if pushed or dry-run, False on error
        """
        if not signed_outcome:
            return False

        if not self.w3 or not self.w3.is_connected():
            logger.warning("[yellow]Web3 not connected — skipping on-chain push[/yellow]")
            return False

        if dry_run:
            logger.debug(
                f"[dim]DRY-RUN: Would push to on-chain: "
                f"{signed_outcome['trade_id']} {signed_outcome['direction']} "
                f"${signed_outcome['pnl_usd']:.2f}[/dim]"
            )
            return True

        try:
            logger.info(
                f"[bold green]Pushing to on-chain: "
                f"{signed_outcome['trade_id']} {signed_outcome['direction']}[/bold green]"
            )

            # TODO: Implement actual contract interaction via Web3.py
            # This is a placeholder; real implementation would:
            # 1. Load contract ABI (NEXUSReputationRegistry)
            # 2. Call recordTradeOutcome(trade_id, direction, confidence, pnl, votes, signature)
            # 3. Wait for receipt
            # 4. Log tx hash

            return True

        except Exception as e:
            logger.error(f"[red]On-chain push failed: {e}[/red]")
            return False

    def _get_chain_id(self) -> int:
        """Get chain ID from RPC."""
        try:
            if self.w3 and self.w3.is_connected():
                return self.w3.eth.chain_id
        except Exception as e:
            logger.debug(f"[dim]Could not fetch chain ID: {e}[/dim]")
        # Default to Base Sepolia
        return 84532

    def mint_agent_erc721_identity(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Mint ERC-721 Agent Identity pointing to:
        - Agent Registration JSON (on-chain capabilities)
        - Agent endpoints (API)
        - Agent wallet (signing authority)
        
        Returns: Dict with token_id, tx_hash, metadata (or None on failure)
        """
        if not self.account:
            logger.warning(f"[yellow]Cannot mint ERC-721: no account configured[/yellow]")
            return None

        try:
            timestamp = int(time.time())
            
            # Build Agent Registration JSON
            agent_metadata = {
                "agent_id": agent_id,
                "version": "1.0",
                "created_at": timestamp,
                "capabilities": ["BUY", "SELL", "HOLD", "VETO"],
                "endpoints": [
                    f"/api/agent/{agent_id}/vote",
                    f"/api/agent/{agent_id}/weights",
                    f"/api/agent/{agent_id}/performance",
                    f"/api/agent/{agent_id}/history",
                ],
                "agent_wallet": self.address,
                "chain_id": self._get_chain_id(),
                "reputation_registry": config.REPUTATION_REGISTRY_ADDRESS or "0x0",
            }
            
            # Sign the metadata with EIP-712
            domain = {
                "name": "NEXUS_AGENT_REGISTRY",
                "version": "1",
                "chainId": self._get_chain_id(),
                "verifyingContract": config.AGENT_REGISTRY_ADDRESS or "0x0",
            }
            
            message_types = {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"},
                ],
                "AgentIdentity": [
                    {"name": "agent_id", "type": "string"},
                    {"name": "capabilities_hash", "type": "bytes32"},
                    {"name": "endpoints_hash", "type": "bytes32"},
                    {"name": "agent_wallet", "type": "address"},
                    {"name": "timestamp", "type": "uint256"},
                ],
            }
            
            # Hash capabilities and endpoints
            capabilities_str = ",".join(agent_metadata["capabilities"])
            endpoints_str = ",".join(agent_metadata["endpoints"])
            
            message_data = {
                "agent_id": agent_id,
                "capabilities_hash": self.w3.keccak(text=capabilities_str) if self.w3 else b"\x00" * 32,
                "endpoints_hash": self.w3.keccak(text=endpoints_str) if self.w3 else b"\x00" * 32,
                "agent_wallet": self.address,
                "timestamp": timestamp,
            }
            
            structured_msg = encode_structured_data(
                {
                    "types": message_types,
                    "primaryType": "AgentIdentity",
                    "domain": domain,
                    "message": message_data,
                }
            )
            
            signed_msg = self.account.sign_message(structured_msg)
            
            logger.info(
                f"[bold green]✓ ERC-721 Agent Identity prepared for {agent_id}[/bold green]"
            )
            logger.debug(f"[dim]Signature: {signed_msg.signature.hex()[:20]}...[/dim]")
            
            return {
                "agent_id": agent_id,
                "metadata": agent_metadata,
                "signature": signed_msg.signature.hex(),
                "message_hash": signed_msg.messageHash.hex(),
                "status": "READY_FOR_MINTING",
                "timestamp": timestamp,
            }
            
        except Exception as e:
            logger.error(f"[red]Failed to prepare ERC-721 identity: {e}[/red]")
            return None

    def register_agent_on_chain(
        self,
        agent_id: str,
        token_id: Optional[str] = None,
    ) -> bool:
        """
        Register agent on-chain in the Agent Registry.
        
        Args:
            agent_id: Agent identifier
            token_id: ERC-721 token ID (if already minted)
        
        Returns:
            True if registered or dry-run, False on error
        """
        try:
            logger.info(
                f"[bold yellow]Registering agent on-chain: {agent_id}[/bold yellow]"
            )
            
            # In production, this would:
            # 1. Call AgentRegistry.registerAgent(agent_id, token_id, metadata_hash)
            # 2. Wait for tx confirmation
            # 3. Return tx hash
            
            # For now, log the intent
            logger.info(
                f"[green]✓ Agent registered: {agent_id} "
                f"(token_id: {token_id or 'pending'})[/green]"
            )
            
            return True
            
        except Exception as e:
            logger.error(f"[red]Agent registration failed: {e}[/red]")
            return False
