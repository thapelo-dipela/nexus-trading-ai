import { createPublicClient, http, erc20Abi } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

const arcTestnet = {
  id: 1143,
  name: 'Arc Testnet',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: { default: { http: ['https://rpc.testnet.arc.network'] } },
} as const;

const USDC = '0x3600000000000000000000000000000000000000' as const;

async function main() {
  const client = createPublicClient({
    chain: arcTestnet,
    transport: http('https://rpc.testnet.arc.network', { 
      timeout: 10_000,
      retryCount: 0,
    }),
  });

  console.log('Calling RPC...');
  const block = await client.getBlockNumber();
  console.log('Block:', block.toString());
}

main().then(() => process.exit(0)).catch(e => { console.error(e); process.exit(1); });
