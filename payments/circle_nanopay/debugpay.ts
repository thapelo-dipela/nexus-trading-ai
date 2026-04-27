import { GatewayClient } from '@circle-fin/x402-batching/client';

async function main() {
  const client = new GatewayClient({
    chain: 'arcTestnet',
    privateKey: process.env.AGENT_WALLET_KEY as `0x${string}`,
  });

  // First check if the seller supports arcTestnet
  const supported = await client.supports('http://localhost:3001/api/crypto/BTC/signals');
  console.log('Supports:', JSON.stringify(supported, null, 2));
}

main().catch(console.error);
