import { ethers } from 'ethers';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';

const GATEWAY_WALLET = '0x0077777d7EBA4688BDeF3E311b846F25870A19B9';
const CHAIN_ID       = 1143;
const DATA_DIR       = path.resolve(__dirname, '../../.nanopay_data');
const RECEIPTS_FILE  = path.join(DATA_DIR, 'receipts.json');
const NONCES_FILE    = path.join(DATA_DIR, 'nonces.json');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

// No provider needed for signing — use ethers.Wallet without connecting to RPC
function getSigner(): ethers.Wallet {
  const pk = (process.env.AGENT_WALLET_KEY || '').trim();
  if (!pk) throw new Error('AGENT_WALLET_KEY not set');
  return new ethers.Wallet(pk); // no provider = no RPC call
}

export async function signPaymentAuthorization(params: {
  toAddress: string;
  amountUSDC: number;
  validForSeconds?: number;
}): Promise<{ signature: string; authorization: object; x402Header: string }> {
  const signer = getSigner();
  const { toAddress, amountUSDC, validForSeconds = 300 } = params;

  const value       = BigInt(Math.round(amountUSDC * 1_000_000));
  const validAfter  = BigInt(Math.floor(Date.now() / 1000) - 10);
  const validBefore = BigInt(Math.floor(Date.now() / 1000) + validForSeconds);
  const nonce       = '0x' + crypto.randomBytes(32).toString('hex');

  const domain = {
    name: 'GatewayWalletBatched',
    version: '1',
    chainId: CHAIN_ID,
    verifyingContract: GATEWAY_WALLET,
  };

  const types = {
    TransferWithAuthorization: [
      { name: 'from',        type: 'address' },
      { name: 'to',          type: 'address' },
      { name: 'value',       type: 'uint256' },
      { name: 'validAfter',  type: 'uint256' },
      { name: 'validBefore', type: 'uint256' },
      { name: 'nonce',       type: 'bytes32' },
    ],
  };

  const message = {
    from:        signer.address,
    to:          toAddress,
    value:       value.toString(),
    validAfter:  validAfter.toString(),
    validBefore: validBefore.toString(),
    nonce,
  };

  const signature = await signer.signTypedData(domain, types, message);

  const payload = {
    scheme: 'exact',
    network: 'arc-testnet',
    payload: { authorization: message, signature },
  };
  const x402Header = Buffer.from(JSON.stringify(payload)).toString('base64');

  persistNonce(nonce);
  return { signature, authorization: message, x402Header };
}

export async function payAndFetch(params: {
  url: string;
  sellerAddress: string;
  amountUSDC: number;
  method?: string;
}): Promise<{ status: number; data: any }> {
  const { url, sellerAddress, amountUSDC, method = 'GET' } = params;

  // Step 1: probe for 402
  const first = await fetch(url, { method });
  if (first.status !== 402) return { status: first.status, data: await first.json() };

  // Step 2: sign offchain (no RPC)
  const { x402Header } = await signPaymentAuthorization({ toAddress: sellerAddress, amountUSDC });

  // Step 3: retry with payment
  const second = await fetch(url, {
    method,
    headers: { 'PAYMENT-SIGNATURE': x402Header },
  });
  const data = await second.json();
  if (second.ok) persistReceipt({ url, amountUSDC, sellerAddress, timestamp: new Date().toISOString() });
  return { status: second.status, data };
}

function persistReceipt(r: any) {
  try {
    const arr = fs.existsSync(RECEIPTS_FILE) ? JSON.parse(fs.readFileSync(RECEIPTS_FILE, 'utf8')) : [];
    arr.push(r);
    fs.writeFileSync(RECEIPTS_FILE, JSON.stringify(arr, null, 2));
  } catch {}
}

function persistNonce(n: string) {
  try {
    const s = new Set(fs.existsSync(NONCES_FILE) ? JSON.parse(fs.readFileSync(NONCES_FILE, 'utf8')) : []);
    s.add(n);
    fs.writeFileSync(NONCES_FILE, JSON.stringify([...s], null, 2));
  } catch {}
}

export function getReceipts() {
  try { return fs.existsSync(RECEIPTS_FILE) ? JSON.parse(fs.readFileSync(RECEIPTS_FILE, 'utf8')) : []; }
  catch { return []; }
}
