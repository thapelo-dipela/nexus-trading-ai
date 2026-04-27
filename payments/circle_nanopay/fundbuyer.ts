import { GatewayClient } from '@circle-fin/x402-batching/client';

async function main() {
  // Use the SELLER wallet to fund the buyer's gateway balance
  const seller = new GatewayClient({
    chain: 'arcTestnet',
    privateKey: process.env.AGENT_WALLET_KEY as `0x${string}`,
  });

  console.log('Depositing 10 USDC for buyer...');
  const result = await seller.depositFor('1', '0x7663cD86a8e9b463b757bb920B75f34e6DF3D113');
  console.log('Deposit tx:', result.depositTxHash);
}

main().catch(console.error);
