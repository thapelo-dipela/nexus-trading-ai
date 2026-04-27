import os
import json
import base64
import time
import logging
from typing import Optional
from agents.base import BaseAgent

logger = logging.getLogger(__name__)

RECEIPTS_FILE = os.path.join(
    os.path.dirname(__file__), '../payments/circle_nanopay/.nanopay_data/receipts.json'
)


class ReceiverAgent(BaseAgent):
    """
    Agent that validates incoming x402 payment responses and tracks receipts.
    On the sell side — confirms payments were made before acting on data.
    """

    def __init__(self, agent_id: str = 'receiver_agent'):
        super().__init__(agent_id=agent_id)

    def validate_receipt(self, response: dict) -> bool:
        """
        Validate a payAndFetch response dict.
        Expects: { status: 200, data: {...} }
        Rejects: 402, errors, missing data.
        """
        if not response:
            return False
        if response.get('error'):
            logger.warning(f'[ReceiverAgent] Payment error: {response["error"]}')
            return False
        if response.get('status') != 200:
            logger.warning(f'[ReceiverAgent] Non-200 status: {response.get("status")}')
            return False
        if not response.get('data'):
            logger.warning('[ReceiverAgent] Empty data in response')
            return False
        return True

    def validate_payment_response_header(self, header: str) -> dict:
        """
        Decode and validate a PAYMENT-RESPONSE header from a seller response.
        Returns parsed payment confirmation or error dict.
        """
        try:
            decoded = json.loads(base64.b64decode(header).decode('utf-8'))
            if not decoded.get('success'):
                return {'valid': False, 'error': 'Payment not confirmed by seller'}
            age = int(time.time()) - decoded.get('settledAt', 0)
            if age > 600:
                return {'valid': False, 'error': f'Stale payment response ({age}s old)'}
            return {
                'valid':      True,
                'payer':      decoded.get('payer'),
                'amount':     decoded.get('amountUSDC'),
                'network':    decoded.get('network'),
                'settled_at': decoded.get('settledAt'),
            }
        except Exception as e:
            return {'valid': False, 'error': f'Could not decode header: {e}'}

    def poll_receipts(self) -> list:
        """Return all stored nanopay receipts from local receipt log."""
        try:
            if os.path.exists(RECEIPTS_FILE):
                with open(RECEIPTS_FILE) as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f'[ReceiverAgent] Could not read receipts: {e}')
        return []

    def latest_receipt(self) -> Optional[dict]:
        receipts = self.poll_receipts()
        return receipts[-1] if receipts else None

    def receipt_count(self) -> int:
        return len(self.poll_receipts())

    def total_spent_usdc(self) -> float:
        return sum(r.get('amountUSDC', 0) for r in self.poll_receipts())

    # Legacy compatibility
    def poll_incoming(self):
        return self.poll_receipts()
