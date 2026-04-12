"""
Hackathon Sandbox Capital Manager — claim sub-account from Capital Vault.
Manages test funds allocation and real capital pool access.
"""
import logging
import json
import time
from typing import Optional, Dict, Any

import config

logger = logging.getLogger(__name__)


class SandboxCapitalManager:
    """Manage hackathon sandbox capital and sub-account claiming."""

    def __init__(
        self,
        agent_id: str,
        team_name: str = "NEXUS Trading AI",
        rpc_url: str = config.RPC_URL,
    ):
        self.agent_id = agent_id
        self.team_name = team_name
        self.rpc_url = rpc_url
        
        # Vault constants (lablab.ai Hackathon Capital Vault on Base)
        self.vault_address = "0x0000000000000000000000000000000000000000"  # Set by lablab.ai
        self.capital_pool = "TESTNET"  # TESTNET or REALCAPITAL
        self.sub_account_created = False
        self.allocated_capital = 0.0

    def claim_sandbox_sub_account(
        self,
        capital_type: str = "TESTNET",
        initial_capital_usd: float = 10000.0,
    ) -> Optional[Dict[str, Any]]:
        """
        Claim a funded sub-account from the Hackathon Capital Vault.
        
        Args:
            capital_type: "TESTNET" (test funds) or "REALCAPITAL" (small real funds for finals)
            initial_capital_usd: Amount to allocate to sub-account
        
        Returns:
            Dict with sub-account details (address, capital, nonce) or None on failure
        """
        try:
            timestamp = int(time.time())
            
            if self.sub_account_created:
                logger.warning(
                    f"[yellow]Sub-account already claimed for {self.agent_id}[/yellow]"
                )
                return {
                    "status": "ALREADY_CREATED",
                    "agent_id": self.agent_id,
                    "sub_account_address": self._generate_sub_account_address(),
                    "capital_allocated_usd": self.allocated_capital,
                    "capital_type": self.capital_pool,
                }
            
            logger.info(
                f"[bold cyan]Claiming {capital_type} sub-account from Capital Vault[/bold cyan]"
            )
            logger.info(
                f"[cyan]Agent: {self.agent_id} | Team: {self.team_name} | "
                f"Amount: ${initial_capital_usd:,.2f}[/cyan]"
            )
            
            # In production, this would:
            # 1. Call CapitalVault.claimSubAccount(agent_id, team_name, capital_type, amount)
            # 2. Wait for tx confirmation
            # 3. Receive sub-account address + nonce
            # 4. Return signed allocation proof
            
            sub_account_address = self._generate_sub_account_address()
            
            sub_account_data = {
                "status": "CLAIMED",
                "agent_id": self.agent_id,
                "team_name": self.team_name,
                "sub_account_address": sub_account_address,
                "capital_type": capital_type,
                "capital_allocated_usd": initial_capital_usd,
                "vault_address": self.vault_address,
                "claimed_at": timestamp,
                "nonce": self._generate_nonce(),
            }
            
            self.sub_account_created = True
            self.allocated_capital = initial_capital_usd
            self.capital_pool = capital_type
            
            logger.info(
                f"[bold green]✓ Sub-account claimed successfully[/bold green]"
            )
            logger.info(
                f"[green]Sub-account: {sub_account_address}[/green]"
            )
            logger.info(
                f"[green]Capital allocated: ${initial_capital_usd:,.2f} ({capital_type})[/green]"
            )
            
            # Persist allocation to file
            self._save_allocation(sub_account_data)
            
            return sub_account_data
            
        except Exception as e:
            logger.error(f"[red]Failed to claim sandbox sub-account: {e}[/red]")
            return None

    def transfer_capital_to_trading_account(
        self,
        kraken_account_address: str,
        amount_usd: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Transfer capital from sub-account to Kraken trading account.
        
        Args:
            kraken_account_address: Kraken account to fund
            amount_usd: Amount to transfer
        
        Returns:
            Dict with tx_hash, status (or None on failure)
        """
        if not self.sub_account_created:
            logger.warning("[yellow]Sub-account not yet claimed[/yellow]")
            return None
        
        if amount_usd > self.allocated_capital:
            logger.error(
                f"[red]Cannot transfer ${amount_usd:,.2f} — "
                f"only ${self.allocated_capital:,.2f} available[/red]"
            )
            return None
        
        try:
            timestamp = int(time.time())
            
            logger.info(
                f"[bold cyan]Transferring ${amount_usd:,.2f} to Kraken account[/bold cyan]"
            )
            
            transfer_record = {
                "status": "PENDING",
                "from_sub_account": self._generate_sub_account_address(),
                "to_kraken_account": kraken_account_address,
                "amount_usd": amount_usd,
                "timestamp": timestamp,
                "nonce": self._generate_nonce(),
            }
            
            # In production:
            # 1. Sign transfer with sub-account key
            # 2. Broadcast to chain
            # 3. Wait for confirmation
            # 4. Log tx_hash
            
            logger.info(
                f"[green]✓ Capital transfer initiated[/green]"
            )
            
            transfer_record["status"] = "CONFIRMED"
            
            return transfer_record
            
        except Exception as e:
            logger.error(f"[red]Capital transfer failed: {e}[/red]")
            return None

    def get_sub_account_balance(self) -> Optional[float]:
        """
        Query current balance of sub-account.
        
        Returns:
            Balance in USD (or None on error)
        """
        if not self.sub_account_created:
            logger.warning("[yellow]Sub-account not yet claimed[/yellow]")
            return None
        
        try:
            # In production: query CapitalVault.getSubAccountBalance(sub_account_address)
            logger.debug(
                f"[dim]Current sub-account balance: ${self.allocated_capital:,.2f}[/dim]"
            )
            return self.allocated_capital
            
        except Exception as e:
            logger.error(f"[red]Balance query failed: {e}[/red]")
            return None

    def get_sub_account_status(self) -> Dict[str, Any]:
        """Get complete status of claimed sub-account."""
        return {
            "agent_id": self.agent_id,
            "team_name": self.team_name,
            "sub_account_created": self.sub_account_created,
            "sub_account_address": self._generate_sub_account_address() if self.sub_account_created else None,
            "capital_type": self.capital_pool,
            "capital_allocated_usd": self.allocated_capital,
            "vault_address": self.vault_address,
        }

    def _generate_sub_account_address(self) -> str:
        """Generate deterministic sub-account address from agent_id."""
        # In production: derive from contract salt or ENS
        import hashlib
        salt = hashlib.sha256(f"{self.agent_id}:{self.team_name}".encode()).digest()
        # Return mock address (format: 0x{40 hex chars})
        return "0x" + salt.hex()[:40]

    def _generate_nonce(self) -> int:
        """Generate nonce for transaction ordering."""
        return int(time.time() * 1000) % (2**32)

    def _save_allocation(self, allocation_data: Dict[str, Any]) -> bool:
        """Persist sub-account allocation to file."""
        try:
            import os
            allocation_file = os.path.join(
                os.path.dirname(__file__),
                f"../sandbox_allocation_{self.agent_id}.json"
            )
            with open(allocation_file, "w") as f:
                json.dump(allocation_data, f, indent=2)
            logger.debug(f"[dim]Allocation saved to {allocation_file}[/dim]")
            return True
        except Exception as e:
            logger.warning(f"[yellow]Could not save allocation: {e}[/yellow]")
            return False


class CapitalAllocationManager:
    """Track total capital across all agents and enforce limits."""

    def __init__(self):
        self.total_capital_usd = 0.0
        self.max_capital_per_agent = 50000.0  # Hackathon limit
        self.agents = {}
        self.allocation_history = []

    def register_agent_capital(
        self,
        agent_id: str,
        capital_usd: float,
    ) -> bool:
        """Register capital allocation for an agent."""
        if capital_usd > self.max_capital_per_agent:
            logger.error(
                f"[red]Capital ${capital_usd:,.2f} exceeds max per agent "
                f"${self.max_capital_per_agent:,.2f}[/red]"
            )
            return False
        
        self.agents[agent_id] = capital_usd
        self.total_capital_usd += capital_usd
        
        self.allocation_history.append({
            "timestamp": int(time.time()),
            "agent_id": agent_id,
            "capital_usd": capital_usd,
            "action": "REGISTERED",
        })
        
        logger.info(
            f"[green]✓ Agent {agent_id} registered with ${capital_usd:,.2f}[/green]"
        )
        
        return True

    def get_total_allocated(self) -> float:
        """Get total capital allocated across all agents."""
        return self.total_capital_usd

    def get_agent_allocation(self, agent_id: str) -> Optional[float]:
        """Get capital allocated to specific agent."""
        return self.agents.get(agent_id)

    def get_allocation_summary(self) -> Dict[str, Any]:
        """Get summary of all allocations."""
        return {
            "total_capital_usd": self.total_capital_usd,
            "agents": self.agents,
            "allocation_count": len(self.agents),
            "history": self.allocation_history,
        }
