import requests
import pandas as pd
from datetime import datetime

# 🔑 CONFIG
ETHERSCAN_API_KEY = "WTXFD5PESHSWTTG1KYDV9Z8F6DFQHDK84AY"
WALLET_ADDRESS = "0x55be7aa03ecfbe37aa5460db791205f7ac9ddca3"

# 📡 Fetch normal transactions
def get_transactions(address):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": "1",
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] != "1":
        print("Error fetching transactions:", data)
        return []

    return data["result"]

# 📡 Fetch ERC20 token transfers
def get_token_transfers(address):
    url = "https://api.etherscan.io/v2/api"
    params = {
        "chainid": "1",
        "module": "account",
        "action": "tokentx",
        "address": address,
        "startblock": "0",
        "endblock": "99999999",
        "sort": "asc",
        "apikey": ETHERSCAN_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data["status"] != "1":
        print("Error fetching token transfers:", data)
        return []

    return data["result"]

# 🔄 Convert raw data into structured format
def process_data(txs, token_txs):
    df_eth = pd.DataFrame()
    df_tokens = pd.DataFrame()

    if txs:
        df_eth = pd.DataFrame([{
            "hash": tx["hash"],
            "timestamp": datetime.fromtimestamp(int(tx["timeStamp"])),
            "from": tx["from"],
            "to": tx["to"],
            "value_eth": int(tx["value"]) / 1e18,
            "gas_used": int(tx["gasUsed"]),
            "is_error": tx["isError"]
        } for tx in txs])

    if token_txs:
        df_tokens = pd.DataFrame([{
            "hash": tx["hash"],
            "timestamp": datetime.fromtimestamp(int(tx["timeStamp"])),
            "token": tx["tokenSymbol"],
            "value": int(tx["value"]) / (10 ** int(tx["tokenDecimal"])),
            "from": tx["from"],
            "to": tx["to"]
        } for tx in token_txs])

    return df_eth, df_tokens

# 🧠 Simple trade inference
def infer_trades(df_tokens, wallet):
    if df_tokens.empty:
        print("No token data found. Skipping trade inference.")
        return pd.DataFrame()

    trades = []

    grouped = df_tokens.groupby("hash")

    for tx_hash, group in grouped:
        tokens_in = group[group["to"].str.lower() == wallet.lower()]
        tokens_out = group[group["from"].str.lower() == wallet.lower()]

        if not tokens_in.empty and not tokens_out.empty:
            trades.append({
                "hash": tx_hash,
                "timestamp": group.iloc[0]["timestamp"],
                "action": "SWAP",
                "token_in": tokens_in.iloc[0]["token"],
                "amount_in": tokens_in.iloc[0]["value"],
                "token_out": tokens_out.iloc[0]["token"],
                "amount_out": tokens_out.iloc[0]["value"]
            })

    return pd.DataFrame(trades)

# 🚀 MAIN PIPELINE
def main():
    print("Fetching transactions...")
    txs = get_transactions(WALLET_ADDRESS)

    print("Fetching token transfers...")
    token_txs = get_token_transfers(WALLET_ADDRESS)

    print("Processing data...")
    df_eth, df_tokens = process_data(txs, token_txs)

    print("Inferring trades...")
    df_trades = infer_trades(df_tokens, WALLET_ADDRESS)

    if df_trades.empty:
        print("No trades detected.")
    else:
        print("\n=== SAMPLE TRADES ===")
        print(df_trades.head())

    df_trades.to_csv("wallet_trades.csv", index=False)
    print("\nSaved to wallet_trades.csv")

if __name__ == "__main__":
    main()