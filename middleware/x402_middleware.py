# x402_middleware.py — x402 with pure-Python EIP-712 signature verification
import os, json, base64, time, logging, functools
from flask import request, jsonify, g, Response

logger = logging.getLogger(__name__)

SELLER_ADDRESS         = os.getenv('SELLER_WALLET_ADDRESS', '')
USDC_ADDRESS           = '0x3600000000000000000000000000000000000000'
GATEWAY_WALLET_ADDRESS = '0x0077777d7EBA4688BDeF3E311b846F25870A19B9'
NETWORK                = os.getenv('PAYMENT_NETWORK', 'arc-testnet')
CHAIN_ID = 1143

def build_payment_required_header(amount_usdc: float, description: str = '') -> str:
    payload = {
        'version': 1,
        'schemes': [{
            'scheme': 'exact',
            'network': NETWORK,
            'maxAmountRequired': str(int(amount_usdc * 1_000_000)),
            'resource': request.url,
            'description': description or f'Access to {request.path}',
            'payTo': SELLER_ADDRESS,
            'requiredDeadlineSeconds': 300,
            'usdcAddress': USDC_ADDRESS,
            'gatewayWalletAddress': GATEWAY_WALLET_ADDRESS,
        }],
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()

def verify_eip3009_signature(payment_sig: str, amount_usdc: float) -> dict:
    import requests as _requests
    circle_key = os.getenv('CIRCLE_API_KEY', '')
    if circle_key:
        try:
            raw     = base64.b64decode(payment_sig).decode('utf-8')
            payload = json.loads(raw)
            resp = _requests.post(
                'https://gateway-api-testnet.circle.com/v1/verify',
                headers={
                    'Authorization': f'Bearer {circle_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'paymentPayload': payload,
                    'paymentRequirements': {
                        'scheme': 'exact',
                        'network': f'eip155:{CHAIN_ID}',
                        'amount': str(int(amount_usdc * 1_000_000)),
                        'payTo': SELLER_ADDRESS,
                        'maxTimeoutSeconds': 300,
                        'extra': {
                            'name': 'GatewayWalletBatched',
                            'version': '1',
                            'verifyingContract': GATEWAY_WALLET_ADDRESS,
                        }
                    }
                },
                timeout=10
            )
            data = resp.json()
            if resp.ok and data.get('isValid'):
                return {'valid': True, 'payer': data.get('payer', ''), 'amount': amount_usdc}
            return {'valid': False, 'error': data.get('invalidReason', 'Circle verification failed')}
        except Exception as e:
            logger.warning(f'[x402] Circle API verify failed: {e}, falling back to local')
    from eth_account import Account
    from eth_account.messages import encode_typed_data
    try:
        raw     = base64.b64decode(payment_sig).decode('utf-8')
        payload = json.loads(raw)
        auth    = payload['payload']['authorization']
        sig     = payload['payload']['signature']
    except Exception as e:
        return {'valid': False, 'error': f'Malformed payload: {e}'}

    now = int(time.time())
    if now > int(auth.get('validBefore', 0)):
        return {'valid': False, 'error': 'Authorization expired'}
    if now < int(auth.get('validAfter', 0)):
        return {'valid': False, 'error': 'Authorization not yet valid'}

    required = int(amount_usdc * 1_000_000)
    if int(auth.get('value', 0)) < required:
        return {'valid': False, 'error': f'Insufficient: {auth.get("value")} < {required}'}

    try:
        full_message = {
            'types': {
                'EIP712Domain': [
                    {'name': 'name',              'type': 'string'},
                    {'name': 'version',           'type': 'string'},
                    {'name': 'chainId',           'type': 'uint256'},
                    {'name': 'verifyingContract', 'type': 'address'},
                ],
                'TransferWithAuthorization': [
                    {'name': 'from',        'type': 'address'},
                    {'name': 'to',          'type': 'address'},
                    {'name': 'value',       'type': 'uint256'},
                    {'name': 'validAfter',  'type': 'uint256'},
                    {'name': 'validBefore', 'type': 'uint256'},
                    {'name': 'nonce',       'type': 'bytes32'},
                ],
            },
            'primaryType': 'TransferWithAuthorization',
            'domain': {
                'name': 'GatewayWalletBatched',
                'version': '1',
                'chainId': CHAIN_ID,
                'verifyingContract': GATEWAY_WALLET_ADDRESS,
            },
            'message': {
                'from':        auth['from'],
                'to':          auth['to'],
                'value':       int(auth['value']),
                'validAfter':  int(auth['validAfter']),
                'validBefore': int(auth['validBefore']),
                'nonce':       auth['nonce'],
            }
        }
        structured = encode_typed_data(full_message=full_message)
        recovered  = Account.recover_message(structured, signature=sig)
        if recovered.lower() != auth['from'].lower():
            return {'valid': False, 'error': f'Signer mismatch: {recovered} != {auth["from"]}'}
        return {'valid': True, 'payer': recovered, 'amount': int(auth['value']) / 1_000_000}
    except Exception as e:
        return {'valid': False, 'error': f'Recovery failed: {e}'}

def require_x402_payment(amount_usdc: float = 0.0001, description: str = ''):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            payment_sig = request.headers.get('PAYMENT-SIGNATURE')
            if not payment_sig:
                resp = jsonify({
                    'error': 'Payment Required',
                    'x402Version': 1,
                    'accepts': [{'scheme': 'exact', 'network': NETWORK,
                                 'maxAmountRequired': str(int(amount_usdc * 1_000_000)),
                                 'payTo': SELLER_ADDRESS}],
                })
                resp.status_code = 402
                resp.headers['PAYMENT-REQUIRED'] = build_payment_required_header(amount_usdc, description)
                return resp

            result = verify_eip3009_signature(payment_sig, amount_usdc)
            if not result['valid']:
                logger.warning(f'[x402] Invalid payment: {result.get("error")}')
                return jsonify({'error': 'Payment verification failed', 'reason': result.get('error')}), 402

            g.x402_payer       = result.get('payer')
            g.x402_amount_usdc = result.get('amount')

            resource_response = f(*args, **kwargs)

            payment_response = base64.b64encode(json.dumps({
                'success': True,
                'payer': result.get('payer'),
                'amountUSDC': result.get('amount'),
                'network': NETWORK,
                'settledAt': int(time.time()),
            }).encode()).decode()

            if isinstance(resource_response, Response):
                resource_response.headers['PAYMENT-RESPONSE'] = payment_response
                return resource_response
            if isinstance(resource_response, tuple):
                resp_obj, *rest = resource_response
                if isinstance(resp_obj, dict):
                    resp_obj = jsonify(resp_obj)
                resp_obj.headers['PAYMENT-RESPONSE'] = payment_response
                return (resp_obj, *rest)
            return resource_response
        return wrapper
    return decorator
