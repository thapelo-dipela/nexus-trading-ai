import { ethers } from './node_modules/ethers/dist/ethers.min.js';

const RPC = 'https://rpc.testnet.arc.network';
const PRIVATE_KEY = '0x076f5d64a7ad0b7f5b5bba0cc191ae017faad45cc2bea74ab68936c1b58b2b04';
const GATEWAY = '0x0077777d7EBA4688BDeF3E311b846F25870A19B9';
const USDC = '0x3600000000000000000000000000000000000000';

const provider = new ethers.JsonRpcProvider(RPC);
const wallet = new ethers.Wallet(PRIVATE_KEY, provider);

console.log('Wallet:', wallet.address);

const usdc = new ethers.Contract(USDC, [
  'function balanceOf(address) view returns (uint256)',
  'function approve(address,uint256) returns (bool)',
  'function decimals() view returns (uint8)',
], wallet);

const bal = await usdc.balanceOf(wallet.address);
const dec = await usdc.decimals();
console.log('USDC balance:', ethers.formatUnits(bal, dec));

// Deposit 10 USDC into Gateway Wallet
const DEPOSIT = ethers.parseUnits('10', dec);

const gatewayAbi = ['function deposit(address token, uint256 value)'];
const gateway = new ethers.Contract(GATEWAY, gatewayAbi, wallet);

console.log('Approving 10 USDC...');
const approveTx = await usdc.approve(GATEWAY, DEPOSIT);
await approveTx.wait();
console.log('Approved:', approveTx.hash);

console.log('Depositing 10 USDC to Gateway Wallet...');
const depositTx = await gateway.deposit(USDC, DEPOSIT);
await depositTx.wait();
console.log('Deposited:', depositTx.hash);
