const res = await fetch('https://rpc.testnet.arc.network', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ jsonrpc: '2.0', method: 'eth_blockNumber', params: [], id: 1 }),
});
const data = await res.json();
console.log('Result:', data);
