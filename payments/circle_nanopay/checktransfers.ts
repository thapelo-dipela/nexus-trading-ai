async function main() {
  const resp = await fetch(
    'https://gateway-api-testnet.circle.com/v1/x402/transfers?network=eip155:5042002',
    {
      headers: {
        'Authorization': `Bearer TEST_API_KEY:57984fe01bcb15fa197f1d9b0a159764:ac4a4dffa3da5fa661d878f3395df299`
      }
    }
  );
  const data = await resp.json();
  console.log(JSON.stringify(data, null, 2));
}
main().catch(console.error);
