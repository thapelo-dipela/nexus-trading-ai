import { GatewayClient } from '@circle-fin/x402-batching/client';

async function main() {
  const client = new GatewayClient({
    chain: 'arcTestnet',
    privateKey: process.env.AGENT_WALLET_KEY as `0x${string}`,
  });
  const balances = await client.getBalances();
  console.log('Gateway balance:', balances.gateway.formattedAvailable, 'USDC');
  console.log('Wallet balance:', balances.wallet.formatted, 'USDC');
}

main().catch(console.error);
