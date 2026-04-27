import { GatewayClient } from '@circle-fin/x402-batching/client';

async function main() {
  const client = new GatewayClient({
    chain: 'arcTestnet',
    privateKey: process.env.AGENT_WALLET_KEY as `0x${string}`,
  });
  const balances = await client.getBalances();
  console.log('Wallet USDC:', balances.wallet.formatted);
  console.log('Gateway available:', balances.gateway.formattedAvailable);
  console.log('Gateway total:', balances.gateway.formattedTotal);
}

main().catch(console.error);
