"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.signPaymentAuthorization = signPaymentAuthorization;
exports.payAndFetch = payAndFetch;
exports.getReceipts = getReceipts;
const ethers_1 = require("ethers");
const crypto_1 = __importDefault(require("crypto"));
const fs_1 = __importDefault(require("fs"));
const path_1 = __importDefault(require("path"));
const GATEWAY_WALLET = '0x0077777d7EBA4688BDeF3E311b846F25870A19B9';
const CHAIN_ID = 1143;
const DATA_DIR = path_1.default.resolve(__dirname, '../../.nanopay_data');
const RECEIPTS_FILE = path_1.default.join(DATA_DIR, 'receipts.json');
const NONCES_FILE = path_1.default.join(DATA_DIR, 'nonces.json');
if (!fs_1.default.existsSync(DATA_DIR))
    fs_1.default.mkdirSync(DATA_DIR, { recursive: true });
// No provider needed for signing — use ethers.Wallet without connecting to RPC
function getSigner() {
    const pk = (process.env.AGENT_WALLET_KEY || '').trim();
    if (!pk)
        throw new Error('AGENT_WALLET_KEY not set');
    return new ethers_1.ethers.Wallet(pk); // no provider = no RPC call
}
async function signPaymentAuthorization(params) {
    const signer = getSigner();
    const { toAddress, amountUSDC, validForSeconds = 300 } = params;
    const value = BigInt(Math.round(amountUSDC * 1000000));
    const validAfter = BigInt(Math.floor(Date.now() / 1000) - 10);
    const validBefore = BigInt(Math.floor(Date.now() / 1000) + validForSeconds);
    const nonce = '0x' + crypto_1.default.randomBytes(32).toString('hex');
    const domain = {
        name: 'GatewayWalletBatched',
        version: '1',
        chainId: CHAIN_ID,
        verifyingContract: GATEWAY_WALLET,
    };
    const types = {
        TransferWithAuthorization: [
            { name: 'from', type: 'address' },
            { name: 'to', type: 'address' },
            { name: 'value', type: 'uint256' },
            { name: 'validAfter', type: 'uint256' },
            { name: 'validBefore', type: 'uint256' },
            { name: 'nonce', type: 'bytes32' },
        ],
    };
    const message = {
        from: signer.address,
        to: toAddress,
        value: value.toString(),
        validAfter: validAfter.toString(),
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
async function payAndFetch(params) {
    const { url, sellerAddress, amountUSDC, method = 'GET' } = params;
    // Step 1: probe for 402
    const first = await fetch(url, { method });
    if (first.status !== 402)
        return { status: first.status, data: await first.json() };
    // Step 2: sign offchain (no RPC)
    const { x402Header } = await signPaymentAuthorization({ toAddress: sellerAddress, amountUSDC });
    // Step 3: retry with payment
    const second = await fetch(url, {
        method,
        headers: { 'PAYMENT-SIGNATURE': x402Header },
    });
    const data = await second.json();
    if (second.ok)
        persistReceipt({ url, amountUSDC, sellerAddress, timestamp: new Date().toISOString() });
    return { status: second.status, data };
}
function persistReceipt(r) {
    try {
        const arr = fs_1.default.existsSync(RECEIPTS_FILE) ? JSON.parse(fs_1.default.readFileSync(RECEIPTS_FILE, 'utf8')) : [];
        arr.push(r);
        fs_1.default.writeFileSync(RECEIPTS_FILE, JSON.stringify(arr, null, 2));
    }
    catch { }
}
function persistNonce(n) {
    try {
        const s = new Set(fs_1.default.existsSync(NONCES_FILE) ? JSON.parse(fs_1.default.readFileSync(NONCES_FILE, 'utf8')) : []);
        s.add(n);
        fs_1.default.writeFileSync(NONCES_FILE, JSON.stringify([...s], null, 2));
    }
    catch { }
}
function getReceipts() {
    try {
        return fs_1.default.existsSync(RECEIPTS_FILE) ? JSON.parse(fs_1.default.readFileSync(RECEIPTS_FILE, 'utf8')) : [];
    }
    catch {
        return [];
    }
}
