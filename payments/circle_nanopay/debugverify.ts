import { GatewayClient, BatchFacilitatorClient } from '@circle-fin/x402-batching/client';

async function main() {
  // We need to intercept the payment payload before it gets sent to verify
  // Patch fetch to log Circle API calls
  const origFetch = global.fetch;
  global.fetch = async (url: any, opts: any) => {
    const res = await origFetch(url, opts);
    if (url.toString().includes('circle.com')) {
      const clone = res.clone();
      const body = await clone.json();
      console.log('Circle API:', url.toString());
      console.log('Response:', JSON.stringify(body, null, 2));
    }
    return res;
  };

  const client = new GatewayClient({
    chain: 'arcTestnet',
    privateKey: process.env.AGENT_WALLET_KEY as `0x${string}`,
  });

  await client.pay('http://localhost:3001/api/crypto/BTC/signals').catch(e => console.log('Error:', e.message));
}

main().catch(console.error);
