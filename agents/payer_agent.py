import os
import json
import subprocess
import logging
from typing import Optional
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

DASHBOARD_URL   = os.getenv('DASHBOARD_URL', 'http://localhost:3000')
SELLER_ADDRESS  = os.getenv('SELLER_WALLET_ADDRESS', '')
NANOPAY_DIR     = os.path.join(os.path.dirname(__file__), '../payments/circle_nanopay')
TSX_BIN         = os.path.join(NANOPAY_DIR, 'node_modules/.bin/tsx')
NANOPAY_TS      = os.path.join(NANOPAY_DIR, 'src/nanopay.ts')
ENV_FILE        = os.path.join(os.path.dirname(__file__), '../.env')

# Endpoint registry — maps action names to (path, cost)
PAID_ENDPOINTS = {
    'signals':     ('/api/crypto/{symbol}/signals', 0.000001),
    'agents':      ('/api/agents',                  0.000001),
    'consensus':   ('/api/consensus',               0.000001),
    'risk':        ('/api/risk',                    0.000001),
    'performance': ('/api/performance',             0.000001),
}


class PayerAgent(BaseAgent):
    """Agent that pays for NEXUS API endpoints via x402 EIP-3009 nanopayments."""

    def __init__(self, agent_id: str = 'payer_agent'):
        super().__init__(agent_id=agent_id)

    def pay_and_fetch(self, action: str, symbol: str = 'BTC',
                      amount_usdc: Optional[float] = None) -> dict:
        """
        Pay for and fetch a protected NEXUS endpoint.
        action: one of 'signals', 'agents', 'consensus', 'risk', 'performance'
        """
        if action not in PAID_ENDPOINTS:
            raise ValueError(f"Unknown action '{action}'. Valid: {list(PAID_ENDPOINTS)}")

        path, default_cost = PAID_ENDPOINTS[action]
        cost = amount_usdc or default_cost
        url  = DASHBOARD_URL + path.format(symbol=symbol)

        script = f"""
import {{ payAndFetch }} from '{NANOPAY_TS}';
payAndFetch({{
  url: '{url}',
  sellerAddress: '{SELLER_ADDRESS}',
  amountUSDC: {cost}
}}).then(r => process.stdout.write(JSON.stringify(r))).catch(e => {{
  process.stdout.write(JSON.stringify({{error: e.message}}));
}});
"""
        try:
            result = subprocess.run(
                [TSX_BIN, '--env-file', ENV_FILE, tmp_path],
                capture_output=True, text=True, timeout=15,
                cwd=NANOPAY_DIR
            )
            if result.returncode != 0 and result.stderr:
                logger.warning(f'[PayerAgent] stderr: {result.stderr[:200]}')
            return json.loads(result.stdout)
        except subprocess.TimeoutExpired:
            return {'error': 'Payment timed out', 'status': 408}
        except json.JSONDecodeError:
            return {'error': f'Invalid response: {result.stdout[:100]}'}
        except Exception as e:
            return {'error': str(e)}

    def get_signals(self, symbol: str = 'BTC') -> dict:
        return self.pay_and_fetch('signals', symbol=symbol)

    def get_consensus(self) -> dict:
        return self.pay_and_fetch('consensus')

    def get_risk(self) -> dict:
        return self.pay_and_fetch('risk')

    def get_agents(self) -> dict:
        return self.pay_and_fetch('agents')

    def get_performance(self) -> dict:
        return self.pay_and_fetch('performance')

    # Legacy compatibility
    def pay_for_action(self, action_id: str, amount_usdc: float,
                       metadata: Optional[dict] = None) -> dict:
        action = action_id.split('_')[0] if '_' in action_id else action_id
        if action in PAID_ENDPOINTS:
            return self.pay_and_fetch(action, amount_usdc=amount_usdc)
        return {'error': f'Unknown action: {action_id}'}
