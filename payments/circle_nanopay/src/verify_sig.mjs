import { ethers } from './node_modules/ethers/dist/ethers.min.js';

const GATEWAY = '0x0077777d7EBA4688BDeF3E311b846F25870A19B9';
const CHAIN_ID = 1143;

const input = JSON.parse(process.argv[2]);
const { authorization: auth, signature: sig } = input.payload;

const domain = {
  name: 'GatewayWalletBatched', version: '1',
  chainId: CHAIN_ID, verifyingContract: GATEWAY,
};
const types = {
  TransferWithAuthorization: [
    { name: 'from', type: 'address' }, { name: 'to', type: 'address' },
    { name: 'value', type: 'uint256' }, { name: 'validAfter', type: 'uint256' },
    { name: 'validBefore', type: 'uint256' }, { name: 'nonce', type: 'bytes32' },
  ],
};

const now = Math.floor(Date.now() / 1000);
if (now > parseInt(auth.validBefore)) {
  console.log(JSON.stringify({ valid: false, error: 'Expired' })); process.exit(0);
}

try {
  const recovered = ethers.verifyTypedData(domain, types, auth, sig);
  const valid = recovered.toLowerCase() === auth.from.toLowerCase();
  console.log(JSON.stringify({ valid, payer: recovered, amount: parseInt(auth.value) / 1e6 }));
} catch (e) {
  console.log(JSON.stringify({ valid: false, error: e.message }));
}
