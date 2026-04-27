"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = require("express");
const ethers_1 = require("ethers");
const nanopay_1 = require("./nanopay");
const router = (0, express_1.Router)();
const RPC = process.env.ARC_RPC_URL || 'https://rpc.testnet.arc.network';
const USDC = process.env.ARC_USDC_ADDRESS || '0x3600000000000000000000000000000000000000';
const ERC20_ABI = [
    'function transfer(address to, uint256 amount) returns (bool)',
    'function decimals() view returns (uint8)',
];
function getWallet() {
    const pk = (process.env.AGENT_WALLET_KEY || '').trim();
    if (!pk)
        throw new Error('AGENT_WALLET_KEY not set');
    return new ethers_1.ethers.Wallet(pk, new ethers_1.ethers.JsonRpcProvider(RPC));
}
router.post('/batch-charge', async (req, res) => {
    try {
        const { actions } = req.body;
        if (!Array.isArray(actions) || actions.length === 0)
            return res.status(400).json({ success: false, error: 'actions array required' });
        const wallet = getWallet();
        const usdc = new ethers_1.ethers.Contract(USDC, ERC20_ABI, wallet);
        const decimals = await usdc.decimals();
        const feeData = await wallet.provider.getFeeData();
        const baseNonce = await wallet.provider.getTransactionCount(wallet.address, 'pending');
        const txPromises = actions.map((a, i) => {
            const amount = ethers_1.ethers.parseUnits(Number(a.amountUSDC).toFixed(6), decimals);
            const to = a.to || a.toAddress || process.env.SELLER_WALLET_ADDRESS || wallet.address;
            return usdc.transfer(to, amount, {
                maxPriorityFeePerGas: 1n,
                maxFeePerGas: feeData.gasPrice ?? undefined,
                nonce: baseNonce + i,
            });
        });
        const txs = await Promise.all(txPromises);
        const recs = await Promise.all(txs.map((tx) => tx.wait()));
        const receipts = actions.map((a, i) => ({
            channelId: a.channelId,
            amountUSDC: a.amountUSDC,
            from: wallet.address,
            to: a.to || a.toAddress,
            txHash: recs[i].hash,
            blockNumber: recs[i].blockNumber,
            timestamp: new Date().toISOString(),
            chain: 'arc-testnet',
        }));
        res.json({ success: true, result: { receipts, actionsCount: actions.length } });
    }
    catch (err) {
        res.status(500).json({ success: false, error: err.message || String(err) });
    }
});
router.post('/sign', async (req, res) => {
    try {
        const { toAddress, amountUSDC, validForSeconds } = req.body;
        const result = await (0, nanopay_1.signPaymentAuthorization)({ toAddress, amountUSDC, validForSeconds });
        res.json({ success: true, result });
    }
    catch (err) {
        res.status(500).json({ success: false, error: err.message || String(err) });
    }
});
router.get('/receipts', async (_req, res) => {
    try {
        res.json({ success: true, receipts: (0, nanopay_1.getReceipts)() });
    }
    catch (err) {
        res.status(500).json({ success: false, error: err.message || String(err) });
    }
});
router.get('/_status', async (_req, res) => {
    try {
        res.json({ success: true, agentKey: Boolean(process.env.AGENT_WALLET_KEY), network: 'arc-testnet' });
    }
    catch (err) {
        res.status(500).json({ success: false, error: String(err) });
    }
});
exports.default = router;
