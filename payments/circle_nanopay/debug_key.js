// Simple debug script to check env variables
const path = require('path');
const dotenv = require('dotenv');

// Try both paths
const envPath1 = path.resolve(__dirname, '../../.env');
const envPath2 = path.resolve(__dirname, '../../../.env');

console.log('From debug script __dirname:', __dirname);
console.log('Path 1 (../../.env):', envPath1, '- Exists:', require('fs').existsSync(envPath1));
console.log('Path 2 (../../../.env):', envPath2, '- Exists:', require('fs').existsSync(envPath2));

// Load from correct path
const correctPath = require('fs').existsSync(envPath1) ? envPath1 : envPath2;
console.log('\nLoading from:', correctPath);

const result = dotenv.config({ path: correctPath });
if (result.error) {
  console.error('Error:', result.error);
} else {
  console.log('Loaded successfully');
}

// Check env vars
const key1 = process.env.SETTLEMENT_PRIVATE_KEY;
const key2 = process.env.AGENT_WALLET_KEY;

console.log('\nSETTLEMENT_PRIVATE_KEY:', key1 ? 'Present (' + key1.length + ' chars)' : 'Missing');
console.log('AGENT_WALLET_KEY:', key2 ? 'Present (' + key2.length + ' chars)' : 'Missing');

const keyToUse = key1 || key2;
if (keyToUse) {
  console.log('\nUsing key:', keyToUse.substring(0, 10) + '...' + keyToUse.substring(keyToUse.length - 4));
  console.log('Matches pattern /^0x[a-fA-F0-9]{64}$/:', /^0x[a-fA-F0-9]{64}$/.test(keyToUse));
  
  // Try creating wallet
  try {
    const ethers = require('ethers');
    const wallet = new ethers.Wallet(keyToUse);
    console.log('✓ Valid wallet! Address:', wallet.address);
  } catch (err) {
    console.log('❌ Error:', err.message);
  }
}

