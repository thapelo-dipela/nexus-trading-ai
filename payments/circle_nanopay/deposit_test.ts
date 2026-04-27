import { createPublicClient, createWalletClient, http, erc20Abi } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';

const arcTestnet = {
  id: 1143,
  name: 'Arc Testnet',
  nativeCurrency: { name: 'Ether', symbol: 'ETH', decimals: 18 },
  rpcUrls: { default: { http: ['https://rpc.testnet.arc.network'] } },
} as const;

const USDC = '0x3600000000000000000000000000000000000000' as const;

async function main() {
  const account = privateKeyToAccount('0x076f5d64a7ad0b7f5b5bba0cc191ae017faad45cc2bea74ab68936c1b58b2b04');
  const transport = http('https://rpc.testnet.arc.network');
  const publicClient = createPublicClient({ chain: arcTestnet, transport });

  const block = await publicClient.getBlockNumber();
  console.log('Connected. Block:', block.toString());
  console.log('Wallet:', account.address);

  const balance = await publicClient.readContract({
    address: USDC,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: [account.address],
  });
  console.log('USDC balance:', Number(balance) / 1_000_000);
}

main().catch(console.error);
